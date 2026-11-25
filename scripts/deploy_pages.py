#!/usr/bin/env python3
"""Publiceer GitHub Pages via het officiële artifact-ID (zonder Twirp-listArtifacts).

De Actions REST API vindt het artifact wel; actions/deploy-pages@v5 vindt
hetzelfde artifact niet via de aparte interne artifactdienst.
"""
import json
import os
import sys
import time
from urllib.parse import urlparse

import requests


def api(method, url, token, payload=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.request(method, url, headers=headers, json=payload, timeout=30)
    if response.status_code >= 400:
        # GitHub-foutmeldingen mogen geen requestheaders of OIDC-token tonen.
        raise RuntimeError(
            f"GitHub Pages API HTTP {response.status_code}: "
            f"{response.text[:600]}"
        )
    return response.json()


def find_artifact(api_root, repository, run_id, token, attempts=9, delay=10):
    """Wacht op uiteindelijke zichtbaarheid van het artifact in de REST API.

    De uploadactie kan succesvol eindigen vóór de artifactlijst van GitHub
    de nieuwe upload teruggeeft. Maximaal 80 seconden bijkomende wachttijd.
    """
    endpoint = f"{api_root}/repos/{repository}/actions/runs/{run_id}/artifacts"
    for attempt in range(1, attempts + 1):
        response = api("GET", endpoint, token)
        matches = [
            art for art in response.get("artifacts", [])
            if art.get("name") == "github-pages"
            and not art.get("expired", False)
        ]
        if len(matches) > 1:
            raise RuntimeError(
                f"Meer dan één 'github-pages'-artifact in run {run_id}; "
                "publicatie afgebroken om verwarring te voorkomen."
            )
        if len(matches) == 1:
            artifact = matches[0]
            if artifact.get("workflow_run", {}).get("id", run_id) != int(run_id):
                raise RuntimeError("Artifact hoort niet bij de huidige workflowrun.")
            return int(artifact["id"])
        if attempt < attempts:
            print(
                f"Artifact nog niet zichtbaar via GitHub REST API "
                f"(poging {attempt}/{attempts}); nieuwe controle over {delay}s.",
                flush=True,
            )
            time.sleep(delay)
    raise RuntimeError(
        f"Geen 'github-pages'-artifact voor run {run_id} na "
        f"{attempts} controles. Controleer het uploadresultaat."
    )


def get_oidc():
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    token = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    response = requests.get(
        url, headers={"Authorization": f"Bearer {token}"}, timeout=20
    )
    response.raise_for_status()
    oidc = response.json().get("value")
    if not oidc:
        raise RuntimeError("GitHub heeft geen OIDC-token aangeleverd.")
    return oidc


def main():
    repository = os.environ["GITHUB_REPOSITORY"]
    run_id = os.environ["GITHUB_RUN_ID"]
    sha = os.environ["GITHUB_SHA"]
    token = os.environ["GH_TOKEN"]
    api_root = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")

    artifact_id = find_artifact(api_root, repository, run_id, token)
    print(f"Publicatiebestand gevonden via GitHub REST API: {artifact_id}", flush=True)

    # OIDC is vereist om het Pages-artifact via de officiële endpoint te deployen.
    # Het token wordt uitsluitend in de beveiligde HTTPS-request meegestuurd.
    oidc = get_oidc()
    result = api(
        "POST",
        f"{api_root}/repos/{repository}/pages/deployments",
        token,
        {
            "artifact_id": artifact_id,
            "environment": "github-pages",
            "pages_build_version": sha,
            "oidc_token": oidc,
        },
    )
    deployment_id = result.get("id")
    if not deployment_id:
        raise RuntimeError("GitHub Pages antwoord bevat geen deployment-ID.")

    page_url = result.get("page_url", "")
    print(f"Pages-deployment aangemaakt: {deployment_id}", flush=True)
    if page_url:
        print(f"Pagina: {page_url}", flush=True)
    status_url = f"{api_root}/repos/{repository}/pages/deployments/{deployment_id}"
    for attempt in range(30):
        # Het deployresultaat kan kort na de POST nog even niet beschikbaar zijn.
        time.sleep(5)
        try:
            status = api("GET", status_url, token).get("status", "").lower()
        except RuntimeError as exc:
            if "HTTP 404" in str(exc) and attempt < 5:
                continue
            raise
        print(f"Pages-status: {status or 'onbekend'}", flush=True)
        if status in ("succeed", "success"):
            print("GitHub Pages succesvol gepubliceerd.", flush=True)
            return 0
        if status in ("errored", "error", "failed", "cancelled"):
            raise RuntimeError(f"GitHub Pages-publicatie mislukt: {status}")
    raise RuntimeError("GitHub Pages-publicatie niet bevestigd binnen 150 seconden.")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Pages-publicatie mislukt: {exc}", file=sys.stderr)
        sys.exit(1)
