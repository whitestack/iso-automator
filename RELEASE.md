# Release Process

This document outlines the process for creating a new release of our project.

## Prerequisites

- You must have push access to the repository.
- Ensure you have the latest `master` branch checked out and up to date.

## Steps to Create a New Release

1. **Create a Release Branch**

   From the `master` branch, create a new branch named `release-X.YY`, where `X.YY` is the version number of the new release. For example:

   ```bash
   git checkout master
   git pull origin master
   git checkout -b release-2.22
   ```

2. **Push the Release Branch**

   Push the new release branch to the remote repository:

   ```bash
   git push -u origin release-2.22
   ```

   This will trigger the GitHub Action to update the `VERSION` file in the release branch.

3. **Make Release-Specific Changes**

   If there are any release-specific changes or last-minute fixes:

   - Make these changes directly on the `release-2.22` branch.
   - Commit and push these changes.
   - Each push will trigger the GitHub Action to update the `VERSION` file and run tests.

4. **Create a Release Tag**

   Once the release branch is stable and all tests are passing, create a tag for the release:

   ```bash
   git checkout release-2.22
   git pull origin release-2.22
   git tag v2.22.0
   git push origin v2.22.0
   ```

5. **Create a GitHub Release**

   - Go to the "Releases" page on your GitHub repository.
   - Click "Draft a new release".
   - Choose the tag you just created (`v2.22.0` in this example).
   - Fill in the release title and description, detailing the changes in this release.
   - If it's a pre-release, mark it as such.
   - Click "Publish release".

6. **Update Master Branch**

   If any critical fixes were made in the release branch, make sure to cherry-pick these commits back to the `master` branch:

   ```bash
   git checkout master
   git cherry-pick <commit-hash>
   git push origin master
   ```

## Maintaining a Release Branch

- For patch releases (e.g., `v2.22.1`), make the changes directly on the `release-2.22` branch.
- Create a new tag for each patch release (e.g., `v2.22.1`, `v2.22.2`, etc.).
- Always ensure the `VERSION` file is updated (this should happen automatically via the GitHub Action).

## Post-Release

- Update any necessary documentation to reflect the new release.
- Communicate the new release to the team and users through appropriate channels.

Remember, the goal is to maintain a stable release branch while allowing development to continue on the `master` branch for the next major release.