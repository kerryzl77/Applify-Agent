import os
import unittest

from app.artifact_models import ArtifactMetadata, CoverLetterArtifact, ParagraphBlock
from app.output_formatter import OutputFormatter


class OutputFormatterTests(unittest.TestCase):
    def test_render_artifact_bundle_creates_matching_docx_and_pdf(self):
        formatter = OutputFormatter()
        artifact = CoverLetterArtifact(
            greeting="Dear Hiring Team,",
            opening=ParagraphBlock(text="I am excited to apply for this role."),
            body=[ParagraphBlock(text="My background aligns with the role's requirements.")],
            closing=ParagraphBlock(text="Thank you for your consideration."),
            metadata=ArtifactMetadata(content_type="cover_letter", company_name="Acme", job_title="Engineer"),
        )
        candidate_data = {
            "personal_info": {
                "name": "Alex Applicant",
                "email": "alex@example.com",
                "phone": "555-111-2222",
                "location": "San Francisco, CA",
            }
        }

        bundle = formatter.render_artifact_bundle(artifact, candidate_data, "user-1", 42)

        self.assertEqual(bundle["artifact_id"], 42)
        self.assertEqual(set(bundle["available_formats"]), {"docx", "pdf"})
        self.assertTrue(os.path.exists(formatter.get_artifact_download_path("user-1", 42, "docx")))
        self.assertTrue(os.path.exists(formatter.get_artifact_download_path("user-1", 42, "pdf")))


if __name__ == "__main__":
    unittest.main()
