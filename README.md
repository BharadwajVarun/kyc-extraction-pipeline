# KYC Extraction Pipeline

A self-hosted, offline-capable KYC document extraction system for
Aadhaar, PAN, and Passport documents.

## Problem
Indian businesses spend 15–30 minutes per customer on manual KYC 
data entry with 3–8% human error rates. Third-party APIs cost 
₹5–15 per document with data privacy risks.

## Solution
A fully offline pipeline that extracts structured fields from KYC 
documents in under 2 seconds with field-level confidence scoring.
Zero cloud dependency — sensitive data stays on-premise.

## Tech Stack
Python · FastAPI · Celery · Redis · PostgreSQL · OpenCV · 
Tesseract · spaCy · MinIO · Docker · Prometheus · Grafana

## Architecture
See docs/architecture.md

## Setup
Coming soon — full docker-compose setup in Week 6.

## Build Log
Following this project post by post on LinkedIn: www.linkedin.com/in/varunbharadwaj