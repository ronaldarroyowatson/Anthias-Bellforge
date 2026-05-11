# Contributing to Bellforge

Bellforge is a derivative of [Anthias](https://github.com/Screenly/Anthias), an open-source digital signage platform.
This guide covers contributing to Bellforge. For upstream contributions to Anthias/Screenly, see the
[upstream repository](https://github.com/Screenly/Anthias/blob/master/CONTRIBUTING.md).

## :seedling: First Steps

Make sure that you have [Git](https://git-scm.com/) installed on your machine.
You can install the [GitHub CLI](https://cli.github.com/) to make it easier to fork and clone repositories and checking out between pull requests.

To get started, fork this Bellforge repository and clone your fork.

```bash
git clone https://github.com/your-username/Bellforge.git
cd Bellforge
```

## :lady_beetle: Creating Issues

When creating an issue, please specify if it's:
- **Bellforge-specific** (custom enhancements, modifications, or issues in this distribution)
- **Upstream-related** (issue that may exist in the original Anthias project)

For upstream issues, consider also reporting to the
[original Anthias project](https://github.com/Screenly/Anthias/issues).

## :bulb: Pull Requests

### Creating Pull Requests

- All pull requests to Bellforge should be made against the `master` branch of
  this repository.
- Please clearly describe whether this is a Bellforge-specific enhancement or a fix that should be
  upstreamed to [Anthias](https://github.com/Screenly/Anthias).
- If this is a bug fix that affects the upstream Anthias project, consider also
  submitting a pull request to the [upstream repository](https://github.com/Screenly/Anthias).
- Add a label to the pull request that describes the changes you made.
  - Add a `bug` label if you are fixing a bug.
  - Add an `enhancement` label if you are adding a new feature or modifying
    existing functionality.
  - Add a `documentation` label if you are updating the documentation.
  - Add a `chore` label if you are doing tasks that don't alter Bellforge's
    functionality.
  - Add a `webview` label if you are making changes to the [WebView](/webview/README.md).
  - Add a `tests` label if you are adding or modifying unit or integration tests.
- Make sure that all of the items in the [checklist](.github/pull_request_template.md) are checked before having it reviewed and merged.
- Don't forget to assign reviewers to your pull request.

### Merging Pull Requests

- All items in the [checklist](.github/pull_request_template.md) should be satisfied before merging.
- For pull requests with more than 5 commits, squash the commits before merging.
