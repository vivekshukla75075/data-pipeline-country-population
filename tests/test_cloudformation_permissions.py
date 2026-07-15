import pathlib
import unittest


class CloudFormationPermissionTests(unittest.TestCase):
    def test_github_actions_deploy_role_allows_log_retention_updates(self) -> None:
        template_path = pathlib.Path(__file__).resolve().parents[1] / "infra" / "cloudformation" / "github-actions-deploy-role.yaml"
        with template_path.open("r", encoding="utf-8") as handle:
            template_text = handle.read()

        self.assertIn("logs:PutRetentionPolicy", template_text)

    def test_orchestration_state_machine_uses_valid_sqs_message_body(self) -> None:
        template_path = pathlib.Path(__file__).resolve().parents[1] / "infra" / "cloudformation" / "orchestration.yaml"
        with template_path.open("r", encoding="utf-8") as handle:
            template_text = handle.read()

        self.assertIn('"MessageBody":', template_text)
        self.assertNotIn('"MessageBody.$"', template_text)

    def test_orchestration_template_does_not_create_lambda_invoke_permissions(self) -> None:
        template_path = pathlib.Path(__file__).resolve().parents[1] / "infra" / "cloudformation" / "orchestration.yaml"
        with template_path.open("r", encoding="utf-8") as handle:
            template_text = handle.read()

        self.assertNotIn("IngestionLambdaInvokePermission", template_text)
        self.assertNotIn("NotificationLambdaInvokePermission", template_text)


if __name__ == "__main__":
    unittest.main()
