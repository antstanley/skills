"""Two-image build for the ``greenfield-features`` suite.

Implements ``docs/benchmark/specs/05-harness-architecture.md`` §Run container
and the integrity rule: per instance we build **two** Docker images from the
same skeleton ``base/`` tree —

- a **run image** (``greenfield-<slug>:run``, the instance's ``dockerImage``)
  carrying ONLY the run-visible ``base/`` tree, with ``jj`` and ``git`` present
  and Python 3.13. The hidden acceptance suite is EXCLUDED.
- a **scoring image** (``greenfield-<slug>:scoring``) = the same base WITH the
  hidden ``hidden/`` tree INCLUDED, so the scoring side can run the withheld
  acceptance suite.

The container backends (tasks 04, 05) provision the run image; the scoring
backend injects/uses the hidden tests via the scoring image. The split is
enforced HERE by the build context the Dockerfile copies: the run build copies
``repo/base`` only; the scoring build copies ``repo/base`` and then overlays
``repo/hidden`` into the checkout at ``hidden/`` (matching the hidden selector
prefix). A suite test asserts the run image has no ``hidden/`` files and the
scoring image does.

Both image tags are named constants (templated on the instance slug). Building
requires Docker; callers in CI without Docker must guard with a daemon probe
(:func:`docker_available`).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from benchmark.suites.greenfield import (
    REPO_HIDDEN_SUBDIR,
    GreenfieldInstanceSpec,
    get_spec,
)

# --- named constants -------------------------------------------------------

#: Base image for both the run and scoring images (small, Python 3.13).
BASE_IMAGE = "python:3.13-slim"

#: Pinned ``jj`` (jujutsu) release installed into the run image. spec-builder
#: selects its workspace backend itself (jj preferred), so the run image ships
#: the real jj binary from the official GitHub release (not a PyPI lookalike).
JJ_VERSION = "v0.41.0"

#: Template for the jj release tarball URL; ``arch`` is detected at build time.
JJ_RELEASE_URL_TEMPLATE = (
    "https://github.com/jj-vcs/jj/releases/download/"
    + JJ_VERSION
    + "/jj-"
    + JJ_VERSION
    + "-${arch}.tar.gz"
)

#: Subdir of an instance ``repo/`` holding the run-visible base tree.
REPO_BASE_SUBDIR = "base"

#: Working directory the skeleton is checked out into inside the image. The
#: hidden suite (scoring image only) is overlaid at ``<WORKDIR>/hidden`` so its
#: selectors (``hidden/...``) resolve verbatim.
IMAGE_WORKDIR = "/workspace"

#: Tag template for the RUN image (hidden tests EXCLUDED). Mirrors
#: ``greenfield.RUN_IMAGE_TAG_TEMPLATE`` / the instance's ``dockerImage``.
RUN_IMAGE_TAG_TEMPLATE = "greenfield-{slug}:run"

#: Tag template for the SCORING image (hidden tests INCLUDED).
SCORING_IMAGE_TAG_TEMPLATE = "greenfield-{slug}:scoring"

#: Build the run image: copy the base skeleton, install jj+git, no hidden tests.
_RUN_DOCKERFILE = f"""\
FROM {BASE_IMAGE}
RUN apt-get update \\
 && apt-get install -y --no-install-recommends git curl ca-certificates \\
 && rm -rf /var/lib/apt/lists/*
# Real jj (jujutsu) binary from the official GitHub release, arch-detected.
RUN set -eux; \\
    case "$(dpkg --print-architecture)" in \\
      arm64) arch=aarch64-unknown-linux-musl ;; \\
      amd64) arch=x86_64-unknown-linux-musl ;; \\
      *) echo "unsupported arch" >&2; exit 1 ;; \\
    esac; \\
    curl -fsSL "{JJ_RELEASE_URL_TEMPLATE}" \\
      | tar -xz -C /usr/local/bin --no-anchored jj; \\
    jj --version
WORKDIR {IMAGE_WORKDIR}
# Run-visible skeleton ONLY. The hidden/ acceptance suite is never copied here.
COPY {REPO_BASE_SUBDIR}/ {IMAGE_WORKDIR}/
"""

#: Build the scoring image: same base, PLUS the hidden suite at ``hidden/``.
_SCORING_DOCKERFILE = f"""\
FROM {BASE_IMAGE}
RUN apt-get update \\
 && apt-get install -y --no-install-recommends git \\
 && rm -rf /var/lib/apt/lists/*
WORKDIR {IMAGE_WORKDIR}
COPY {REPO_BASE_SUBDIR}/ {IMAGE_WORKDIR}/
# Scoring side ONLY: overlay the withheld acceptance suite at hidden/.
COPY {REPO_HIDDEN_SUBDIR}/ {IMAGE_WORKDIR}/{REPO_HIDDEN_SUBDIR}/
"""


def run_image_tag(slug: str) -> str:
    """Return the RUN image tag for instance ``slug`` (its ``dockerImage``)."""
    return RUN_IMAGE_TAG_TEMPLATE.format(slug=slug)


def scoring_image_tag(slug: str) -> str:
    """Return the SCORING image tag for instance ``slug``."""
    return SCORING_IMAGE_TAG_TEMPLATE.format(slug=slug)


def docker_available() -> bool:
    """Return ``True`` iff a reachable Docker daemon answers ``docker info``.

    Used to gate the Docker-dependent build/inspection paths so the suite's
    filesystem/schema tests still run where Docker is absent (e.g. CI).
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _docker_build(dockerfile: str, context: Path, tag: str) -> None:
    """Build ``tag`` from ``dockerfile`` text against the ``context`` dir."""
    result = subprocess.run(
        ["docker", "build", "-t", tag, "-f", "-", str(context)],
        input=dockerfile,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"docker build of {tag} failed:\n{result.stdout}\n{result.stderr}"
        )


def build_run_image(spec: GreenfieldInstanceSpec) -> str:
    """Build the RUN image for ``spec`` (hidden tests EXCLUDED); return its tag.

    The build context is the instance's ``repo/`` dir; the Dockerfile copies
    ``base/`` only, so the hidden suite never enters this image.
    """
    tag = run_image_tag(spec.slug)
    _docker_build(_RUN_DOCKERFILE, spec.repo_source_dir, tag)
    return tag


def build_scoring_image(spec: GreenfieldInstanceSpec) -> str:
    """Build the SCORING image for ``spec`` (hidden tests INCLUDED); return tag."""
    tag = scoring_image_tag(spec.slug)
    _docker_build(_SCORING_DOCKERFILE, spec.repo_source_dir, tag)
    return tag


def build_images(slug: str) -> tuple[str, str]:
    """Build both images for ``slug``; return ``(run_tag, scoring_tag)``."""
    spec = get_spec(slug)
    return build_run_image(spec), build_scoring_image(spec)
