import unittest

from pydantic import ValidationError

from app.artifact_models import (
    ArtifactMetadata,
    CoverLetterArtifact,
    EmailArtifact,
    LinkedInMessageArtifact,
    ParagraphBlock,
)
from app.config import Settings
from app.llm_service import LLMService


class ArtifactModelTests(unittest.TestCase):
    def test_cover_letter_artifact_accepts_valid_shape(self):
        artifact = CoverLetterArtifact(
            greeting="Dear Hiring Team,",
            opening=ParagraphBlock(text="I am excited to apply for the role."),
            body=[ParagraphBlock(text="I have delivered measurable impact across product and engineering teams.")],
            closing=ParagraphBlock(text="I would welcome the chance to discuss the role further."),
            metadata=ArtifactMetadata(content_type="cover_letter", company_name="Acme", job_title="Engineer"),
        )
        self.assertIn("Dear Hiring Team,", artifact.to_plain_text())

    def test_email_artifact_rejects_overlong_body(self):
        long_text = "word " * 260
        with self.assertRaises(ValidationError):
            EmailArtifact(
                subject="Hello",
                greeting="Hi Alex,",
                body=[ParagraphBlock(text=long_text)],
                call_to_action=ParagraphBlock(text="Would love to connect."),
                metadata=ArtifactMetadata(content_type="connection_email", company_name="Acme", job_title="Engineer"),
            )

    def test_linkedin_message_rejects_messages_over_200_characters(self):
        with self.assertRaises(ValidationError):
            LinkedInMessageArtifact(body="x" * 201)

    def test_paragraph_style_must_be_enum(self):
        with self.assertRaises(ValidationError):
            ParagraphBlock(text="Hello", style="flashy")

    def test_llm_service_uses_gpt_5_4_default_model(self):
        settings = Settings()
        service = LLMService()
        self.assertEqual(settings.openai_default_model, "gpt-5.4")
        self.assertEqual(service.model, "gpt-5.4")


if __name__ == "__main__":
    unittest.main()
