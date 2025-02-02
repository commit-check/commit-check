import sys
import pytest
from commit_check.main import main
from commit_check import DEFAULT_CONFIG, PASS, FAIL

CMD = "commit-check"


class TestMain:
    @pytest.mark.parametrize("argv, check_commit_call_count, check_branch_call_count, check_author_call_count, check_commit_signoff_call_count, check_merge_base_call_count", [
        ([CMD, "--message"], 1, 0, 0, 0, 0),
        ([CMD, "--branch"], 0, 1, 0, 0, 0),
        ([CMD, "--author-name"], 0, 0, 1, 0, 0),
        ([CMD, "--author-email"], 0, 0, 1, 0, 0),
        ([CMD, "--commit-signoff"], 0, 0, 0, 1, 0),
        ([CMD, "--merge-base"], 0, 0, 0, 0, 1),
        ([CMD, "--message", "--author-email"], 1, 0, 1, 0, 0),
        ([CMD, "--branch", "--message"], 1, 1, 0, 0, 0),
        ([CMD, "--author-name", "--author-email"], 0, 0, 2, 0, 0),
        ([CMD, "--message", "--branch", "--author-email"], 1, 1, 1, 0, 0),
        ([CMD, "--branch", "--message", "--author-name", "--author-email"], 1, 1, 2, 0, 0),
        ([CMD, "--message", "--branch", "--author-name", "--author-email", "--commit-signoff", "--merge-base"], 1, 1, 2, 1, 1),
        ([CMD, "--dry-run"], 0, 0, 0, 0, 0),
    ])
    def test_main(
            self,
            mocker,
            argv,
            check_commit_call_count,
            check_branch_call_count,
            check_author_call_count,
            check_commit_signoff_call_count,
            check_merge_base_call_count,
    ):
        mocker.patch(
            "commit_check.main.validate_config",
            return_value={
                "checks": [
                    {"check": "dummy_check_type"}
                ]
            }
        )
        m_check_commit = mocker.patch("commit_check.commit.check_commit_msg")
        m_check_branch = mocker.patch("commit_check.branch.check_branch")
        m_check_author = mocker.patch("commit_check.author.check_author")
        m_check_commit_signoff = mocker.patch("commit_check.commit.check_commit_signoff")
        m_check_merge_base = mocker.patch("commit_check.branch.check_merge_base")
        sys.argv = argv
        main()
        assert m_check_commit.call_count == check_commit_call_count
        assert m_check_branch.call_count == check_branch_call_count
        assert m_check_author.call_count == check_author_call_count
        assert m_check_commit_signoff.call_count == check_commit_signoff_call_count
        assert m_check_merge_base.call_count == check_merge_base_call_count

    def test_main_help(self, mocker, capfd):
        mocker.patch(
            "commit_check.main.validate_config",
            return_value={
                "checks": [
                    {"check": "dummy_check_type"}
                ]
            }
        )
        m_check_commit = mocker.patch("commit_check.commit.check_commit_msg")
        m_check_branch = mocker.patch("commit_check.branch.check_branch")
        m_check_author = mocker.patch("commit_check.author.check_author")
        m_check_commit_signoff = mocker.patch("commit_check.commit.check_commit_signoff")
        m_check_merge_base = mocker.patch("commit_check.branch.check_merge_base")
        sys.argv = ["commit-check", "--h"]
        with pytest.raises(SystemExit):
            main()
        assert m_check_commit.call_count == 0
        assert m_check_branch.call_count == 0
        assert m_check_author.call_count == 0
        assert m_check_commit_signoff.call_count == 0
        assert m_check_merge_base.call_count == 0
        stdout, _ = capfd.readouterr()
        assert "usage: " in stdout

    def test_main_version(self, mocker):
        mocker.patch(
            "commit_check.main.validate_config",
            return_value={
                "checks": [
                    {"check": "dummy_check_type"}
                ]
            }
        )
        m_check_commit = mocker.patch("commit_check.commit.check_commit_msg")
        m_check_branch = mocker.patch("commit_check.branch.check_branch")
        m_check_author = mocker.patch("commit_check.author.check_author")
        m_check_commit_signoff = mocker.patch("commit_check.commit.check_commit_signoff")
        m_check_merge_base = mocker.patch("commit_check.branch.check_merge_base")
        sys.argv = ["commit-check", "--v"]
        with pytest.raises(SystemExit):
            main()
        assert m_check_commit.call_count == 0
        assert m_check_branch.call_count == 0
        assert m_check_author.call_count == 0
        assert m_check_commit_signoff.call_count == 0
        assert m_check_merge_base.call_count == 0

    def test_main_validate_config_ret_none(self, mocker):
        mocker.patch(
            "commit_check.main.validate_config",
            return_value={}
        )
        m_check_commit = mocker.patch("commit_check.commit.check_commit_msg")
        mocker.patch("commit_check.branch.check_branch")
        mocker.patch("commit_check.author.check_author")
        mocker.patch("commit_check.commit.check_commit_signoff")
        mocker.patch("commit_check.branch.check_merge_base")
        sys.argv = ["commit-check", "--message"]
        main()
        assert m_check_commit.call_count == 1
        assert m_check_commit.call_args[0][0] == DEFAULT_CONFIG["checks"]

    @pytest.mark.parametrize(
        "argv, message_result, branch_result, author_name_result, author_email_result, commit_signoff_result, merge_base_result, final_result",
        [
            ([CMD, "--message"], PASS, PASS, PASS, PASS, PASS, PASS, PASS),
            ([CMD, "--message"], FAIL, PASS, PASS, PASS, PASS, PASS, FAIL),
            ([CMD, "--message", "--commit-signoff"], FAIL, PASS, PASS, PASS, PASS, PASS, FAIL,),
            ([CMD, "--message", "--commit-signoff"], PASS, PASS, PASS, PASS, FAIL, PASS, FAIL,),
            ([CMD, "--message", "--author-name", "--author-email"], PASS, PASS, PASS, PASS, PASS, PASS, PASS,),
            ([CMD, "--message", "--author-name", "--author-email"], FAIL, PASS, PASS, PASS, PASS, PASS, FAIL,),
            ([CMD, "--message", "--author-name", "--author-email"], PASS, PASS, FAIL, PASS, PASS, PASS, FAIL,),
            ([CMD, "--message", "--author-name", "--author-email"], PASS, PASS, PASS, FAIL, PASS, PASS, FAIL,),
            ([CMD, "--message", "--author-name", "--author-email"], PASS, PASS, FAIL, FAIL, PASS, PASS, FAIL,),
            ([CMD, "--message", "--branch", "--author-name", "--author-email", "--commit-signoff", "--merge-base", ], PASS, PASS, PASS, PASS, PASS, PASS, PASS,),
            ([CMD, "--message", "--branch", "--author-name", "--author-email", "--commit-signoff", "--merge-base", ], FAIL, FAIL, FAIL, FAIL, FAIL, FAIL, FAIL,),
            ([CMD, "--message", "--branch", "--author-name", "--author-email", "--commit-signoff", "--merge-base", ], FAIL, PASS, PASS, PASS, PASS, PASS, FAIL,),
            ([CMD, "--dry-run"], FAIL, FAIL, FAIL, FAIL, FAIL, FAIL, PASS),
        ],
    )
    def test_main_multiple_checks(
        self,
        mocker,
        argv,
        message_result,
        branch_result,
        author_name_result,
        author_email_result,
        commit_signoff_result,
        merge_base_result,
        final_result,
    ):
        mocker.patch(
            "commit_check.main.validate_config",
            return_value={},
        )

        mocker.patch(
            "commit_check.commit.check_commit_msg", return_value=message_result
        )
        mocker.patch(
            "commit_check.commit.check_commit_signoff",
            return_value=commit_signoff_result,
        )

        mocker.patch("commit_check.branch.check_branch", return_value=branch_result)
        mocker.patch(
            "commit_check.branch.check_merge_base", return_value=merge_base_result
        )

        # this is messy. why isn't this a private implementation detail with a
        # public check_author_name and check_author email?
        def author_side_effect(_, check_type: str) -> int:
            assert check_type in ("author_name", "author_email")
            if check_type == "author_name":
                return author_name_result
            elif check_type == "author_email":
                return author_email_result

        mocker.patch("commit_check.author.check_author", side_effect=author_side_effect)
        mocker.patch("commit_check.author.check_author", side_effect=author_side_effect)

        sys.argv = argv
        assert main() == final_result
