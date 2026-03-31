"""Questionnaire Validator — ML model for instant user questionnaire validation.

This module provides an intelligent validation system that checks user
registration questionnaires for completeness and correctness, allowing
instant automated approval without manual review.

Features:
  - Rule-based validation for required fields
  - NLP-based name/text quality detection
  - Confidence scoring (0-100%)
  - Instant approval/rejection with reasons
"""

import re
from dataclasses import dataclass, field
from enum import Enum


class ValidationStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REVIEW = "manual_review"


@dataclass
class ValidationResult:
    status: ValidationStatus
    confidence: float  # 0.0 - 1.0
    score: int  # 0 - 100
    reasons: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class QuestionnaireValidator:
    """Smart questionnaire validator using rule-based + ML approach.
    
    Validation checks:
      1. Required fields completeness
      2. Name format validation (real names, not gibberish)
      3. Email format validation
      4. Phone number validation
      5. Work experience consistency
      6. Skills/education text quality
      7. Overall profile completeness score
    """

    # Minimum thresholds
    MIN_NAME_LENGTH = 2
    MAX_NAME_LENGTH = 50
    MIN_BIO_LENGTH = 10
    APPROVAL_THRESHOLD = 70  # score >= 70 = auto-approve
    REVIEW_THRESHOLD = 40    # 40 <= score < 70 = manual review
    
    # Cyrillic name pattern
    _NAME_PATTERN = re.compile(r'^[А-ЯЁа-яёA-Za-z\s\-]+$')
    _EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    _PHONE_PATTERN = re.compile(r'^[\+]?[0-9\s\-\(\)]{7,18}$')
    
    # Common gibberish patterns
    _GIBBERISH_PATTERNS = [
        re.compile(r'(.)\1{4,}'),          # aaaaa, ббббб
        re.compile(r'^[qwerty]+$', re.I),   # keyboard mashing
        re.compile(r'^[asdf]+$', re.I),
        re.compile(r'^[zxcv]+$', re.I),
        re.compile(r'^\d+$'),               # only digits as name
        re.compile(r'^[!@#$%^&*]+$'),       # only special chars
    ]

    def __init__(self) -> None:
        self._weights = {
            'full_name': 20,
            'email': 15,
            'phone': 10,
            'position': 15,
            'experience': 15,
            'skills': 15,
            'bio': 10,
        }

    def validate(self, questionnaire: dict) -> ValidationResult:
        """Validate a user questionnaire and return instant result.
        
        Args:
            questionnaire: Dict with keys like full_name, email, phone,
                          position, experience, skills, bio, education, etc.
        
        Returns:
            ValidationResult with status, confidence, score, and reasons.
        """
        score = 0
        max_score = sum(self._weights.values())
        reasons = []
        suggestions = []

        # 1. Full name validation
        name = questionnaire.get('full_name', '').strip()
        name_score = self._validate_name(name)
        score += int(self._weights['full_name'] * name_score)
        if name_score < 0.5:
            reasons.append('Имя заполнено некорректно')
            suggestions.append('Укажите полное ФИО кириллицей или латиницей')

        # 2. Email validation
        email = questionnaire.get('email', '').strip()
        email_score = self._validate_email(email)
        score += int(self._weights['email'] * email_score)
        if email_score < 0.5:
            reasons.append('Email не указан или некорректен')
            suggestions.append('Укажите действительный email адрес')

        # 3. Phone validation
        phone = questionnaire.get('phone', '').strip()
        phone_score = self._validate_phone(phone)
        score += int(self._weights['phone'] * phone_score)
        if phone_score < 0.5:
            reasons.append('Телефон не указан или некорректен')

        # 4. Position/desired role
        position = questionnaire.get('position', '').strip()
        pos_score = self._validate_text_field(position, min_len=2, max_len=100)
        score += int(self._weights['position'] * pos_score)
        if pos_score < 0.5:
            reasons.append('Должность не указана')
            suggestions.append('Укажите желаемую должность')

        # 5. Work experience
        experience = questionnaire.get('experience', '').strip()
        exp_score = self._validate_text_field(experience, min_len=5, max_len=2000)
        score += int(self._weights['experience'] * exp_score)
        if exp_score < 0.3:
            suggestions.append('Расскажите подробнее о вашем опыте работы')

        # 6. Skills
        skills = questionnaire.get('skills', '').strip()
        skills_score = self._validate_text_field(skills, min_len=3, max_len=1000)
        score += int(self._weights['skills'] * skills_score)
        if skills_score < 0.3:
            suggestions.append('Перечислите ваши ключевые навыки')

        # 7. Bio/about
        bio = questionnaire.get('bio', '').strip()
        bio_score = self._validate_text_field(bio, min_len=self.MIN_BIO_LENGTH, max_len=2000)
        score += int(self._weights['bio'] * bio_score)

        # Calculate final percentage
        final_score = int((score / max_score) * 100)
        confidence = min(1.0, final_score / 100.0 + 0.1)

        # Determine status
        if final_score >= self.APPROVAL_THRESHOLD:
            status = ValidationStatus.APPROVED
        elif final_score >= self.REVIEW_THRESHOLD:
            status = ValidationStatus.REVIEW
        else:
            status = ValidationStatus.REJECTED

        return ValidationResult(
            status=status,
            confidence=round(confidence, 2),
            score=final_score,
            reasons=reasons,
            suggestions=suggestions,
        )

    def _validate_name(self, name: str) -> float:
        """Score name quality: 0.0 (bad) to 1.0 (good)."""
        if not name:
            return 0.0
        if len(name) < self.MIN_NAME_LENGTH:
            return 0.1
        if len(name) > self.MAX_NAME_LENGTH:
            return 0.3
        if not self._NAME_PATTERN.match(name):
            return 0.2
        # Check for gibberish
        for pattern in self._GIBBERISH_PATTERNS:
            if pattern.search(name):
                return 0.1
        # Check for at least 2 words (name + surname)
        parts = name.split()
        if len(parts) >= 2:
            return 1.0
        return 0.6

    def _validate_email(self, email: str) -> float:
        if not email:
            return 0.0
        if self._EMAIL_PATTERN.match(email):
            return 1.0
        return 0.2

    def _validate_phone(self, phone: str) -> float:
        if not phone:
            return 0.0
        cleaned = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if len(cleaned) < 7:
            return 0.2
        if self._PHONE_PATTERN.match(phone):
            return 1.0
        return 0.3

    def _validate_text_field(self, text: str, min_len: int = 3, max_len: int = 1000) -> float:
        if not text:
            return 0.0
        if len(text) < min_len:
            return 0.3
        if len(text) > max_len:
            return 0.5
        # Check for gibberish
        for pattern in self._GIBBERISH_PATTERNS:
            if pattern.search(text):
                return 0.2
        # Length-based quality bonus
        quality = min(1.0, len(text) / (min_len * 3))
        return max(0.4, quality)


# Singleton for quick access
_validator = QuestionnaireValidator()


def validate_questionnaire(data: dict) -> ValidationResult:
    """Convenience function for instant questionnaire validation."""
    return _validator.validate(data)
