from main import score_file, group_files_by_context, parse_github_url


class TestScoreFile:
    def test_priority_filename_with_priority_extension(self):
        assert score_file("src/main.py") == 15  # +10 'main' pattern, +5 .py

    def test_priority_pattern_inside_compound_name(self):
        assert score_file("src/auth.js") == 15  # +10 'auth' pattern, +5 .js

    def test_test_file_penalty_overrides_priority_match(self):
        assert score_file("tests/test_app.py") == -5  # +10 'app', +5 .py, -20 'test'

    def test_node_modules_penalty(self):
        assert score_file("node_modules/react/index.js") == -35  # +10 'index', +5 .js, -50

    def test_vendor_and_minified_penalty_applies_once(self):
        assert score_file("vendor/lib.min.js") == -45  # +5 .js, -50 (not -100)

    def test_no_pattern_no_priority_extension(self):
        assert score_file("docs/readme.md") == 0

    def test_spec_triggers_same_penalty_as_test(self):
        assert score_file("auth.spec.ts") == -5  # +10 'auth', +5 .ts, -20 'spec'


class TestGroupFilesByContext:
    def test_empty_list_returns_empty(self):
        assert group_files_by_context([]) == []

    def test_single_small_file_single_group(self):
        files = [{"path": "a.py", "size": 100}]
        assert group_files_by_context(files) == [files]

    def test_files_under_limit_grouped_together(self):
        files = [{"path": "a.py", "size": 11250}, {"path": "b.py", "size": 11250}]
        assert group_files_by_context(files) == [files]

    def test_exceeding_limit_starts_new_group(self):
        files = [
            {"path": "a.py", "size": 11250},
            {"path": "b.py", "size": 11250},
            {"path": "c.py", "size": 11250},
        ]
        result = group_files_by_context(files)
        assert result == [[files[0], files[1]], [files[2]]]

    def test_missing_size_defaults_to_zero(self):
        files = [{"path": "a.py"}, {"path": "b.py"}, {"path": "c.py"}]
        assert group_files_by_context(files) == [files]


class TestParseGithubUrl:
    def test_plain_url(self):
        assert parse_github_url("https://github.com/owner/repo") == ("owner", "repo")

    def test_strips_git_suffix(self):
        assert parse_github_url("https://github.com/owner/repo.git") == ("owner", "repo")

    def test_strips_trailing_slash(self):
        assert parse_github_url("https://github.com/owner/repo/") == ("owner", "repo")

    def test_ignores_extra_path_segments(self):
        assert parse_github_url("https://github.com/owner/repo/tree/main") == ("owner", "repo")

    def test_invalid_url_returns_none_tuple(self):
        assert parse_github_url("not a github url") == (None, None)

    def test_ssh_style_url_not_supported(self):
        # known limitation: no slash right after "github.com" in SSH urls
        assert parse_github_url("git@github.com:owner/repo.git") == (None, None)
