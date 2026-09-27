# Launch Axiomathic on GitHub Pages

This guide assumes a new GitHub account and no existing repositories.

## Part 1 - create the repository

1. Sign in to GitHub.
2. Click the **+** menu in the top-right and choose **New repository**.
3. Repository name: `axiomathic`.
4. Description (optional): `Mathematical notes and projects, published from LaTeX.`
5. Choose **Public** if you are using GitHub Free. GitHub Pages is available for public repositories on GitHub Free.
6. Do **not** add a README, `.gitignore`, or licence during creation; this package already contains the first two.
7. Click **Create repository**.

## Part 2 - put these files into GitHub

### Easiest route: GitHub Desktop

1. Install GitHub Desktop and sign in to the same account.
2. Unzip the `axiomathic_github_repo.zip` package supplied by ChatGPT.
3. In GitHub Desktop choose **File > Add local repository...** and select the unzipped `axiomathic` folder.
4. If GitHub Desktop says the folder is not yet a Git repository, choose **Create a repository** there.
5. Commit all files with a message such as `Initial Axiomathic site`.
6. Click **Publish repository**.
7. Make sure its GitHub name is `axiomathic` and publish it to your account.

### Command-line route

From inside the unzipped folder:

```bash
git init
git add .
git commit -m "Initial Axiomathic site"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/axiomathic.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username.

## Part 3 - enable GitHub Pages

1. Open the `axiomathic` repository on GitHub.
2. Click **Settings**.
3. In the left sidebar, under **Code, planning, and automation**, click **Pages**.
4. Under **Build and deployment > Source**, choose **GitHub Actions**.
5. Do not create one of GitHub's suggested starter workflows: this repository already contains `.github/workflows/pages.yml`.
6. Click the **Actions** tab. You should see **Build and publish Axiomathic** running (or already completed).
7. Open that workflow run. Both the `build` and `deploy` jobs should finish with green ticks.
8. Return to **Settings > Pages** and use **Visit site** once GitHub shows the deployed URL.

For a project repository named `axiomathic`, the default address is normally:

```text
https://YOUR-USERNAME.github.io/axiomathic/
```

GitHub notes that a new deployment can take several minutes to appear.

## Part 4 - connect your custom domain (optional, after the default site works)

Do this only after the `github.io/axiomathic/` version is working.

1. In the repository go to **Settings > Pages**.
2. Under **Custom domain**, enter the domain you want for Axiomathic and save it.
3. At your DNS provider:
   - For a subdomain such as `www.example.com`, create a `CNAME` pointing to `YOUR-USERNAME.github.io` (do not append `/axiomathic`).
   - For an apex/root domain such as `example.com`, use the GitHub Pages `A`/`AAAA` records or an `ALIAS`/`ANAME` supported by your provider.
4. Wait for DNS propagation and GitHub's domain check.
5. Once available, enable **Enforce HTTPS** in **Settings > Pages**.

GitHub recommends verifying a custom domain before relying on it, and warns against wildcard DNS records for Pages.

## Part 5 - your normal publishing workflow afterwards

You do not manually export HTML. Just edit the LaTeX and push the change:

```bash
git add .
git commit -m "Update Waring notes"
git push
```

Every push to `main` automatically rebuilds both the PDF and the website.

## Adding another chapter

Create another file in `sections/`, following the existing `subfiles` pattern, for example:

```tex
\documentclass[../Axiomathic.tex]{subfiles}
\begin{document}
\chapter{A New Topic}
...
\end{document}
```

Then add one line to `Axiomathic.tex`:

```tex
\subfile{sections/A New Topic}
```

The next GitHub build automatically adds the chapter to the contents/navigation and generates its own HTML page.
