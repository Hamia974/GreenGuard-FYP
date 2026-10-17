# CLAUDE.md

# GreenGuard Development Guide

This document defines the permanent development rules for the GreenGuard project.

Claude Code must always follow these instructions unless explicitly overridden by the project owner.

---

# Project Overview

Project Name

GreenGuard

GreenGuard is a production-grade AI-powered Plant Health Monitoring and Agricultural Decision Support System designed to help farmers diagnose crop health through a modular multi-stage architecture.

The system consists of three independent AI modules plus an application-level report:

• Module 1 – Disease Detection (live service)
• Module 2 – Soil & Nutrient Health (live service)
• Module 3 – Weather Risk Assessment (local service, Open-Meteo)
• Module 4 – Integrated Analysis Report (application layer — NOT an AI model)

Each AI module performs a single responsibility and returns a standardized JSON response.

The backend is responsible for orchestrating these modules and storing their outputs side by side as one analysis report. There is no Fusion model: the backend never combines results into a final diagnosis, combined confidence or recommendations.

This project is a production-quality Final Year Project and should never be treated as a demo application.

---

# Architecture

Always follow the architecture exactly.

GreenGuard follows a Layered Architecture implemented using a Client–Server Model.

Presentation Layer
↓

Business Logic Layer
↓

AI Integration Layer
↓

AI Processing Modules
↓

Data Layer

The frontend communicates ONLY with Django REST APIs.

The backend communicates with independent AI modules.

The frontend must NEVER communicate directly with AI models.

The backend acts as the orchestrator for all AI modules.

Never bypass the backend.

---

# Technology Stack

## Frontend

Next.js 15

TypeScript

Tailwind CSS

shadcn/ui

Framer Motion

React Hook Form

Zod

Axios

TanStack Query

Lucide React

## Backend

Python

Django

Django REST Framework

Simple JWT

Pillow

django-filter

## Database

PostgreSQL

Use Django ORM.

Never use MongoDB.

## AI

TensorFlow

PyTorch

OpenCV

The AI models are developed independently and exposed through APIs.

---

# Project Structure

Always maintain this structure.

GreenGuard/

frontend/

backend/

docs/

README.md

CLAUDE.md

Never create unnecessary folders.

Keep the project modular.

---

# Coding Standards

Always write clean production-ready code.

Avoid code duplication.

Use reusable components.

Use modular architecture.

Follow SOLID principles.

Keep files small.

Split large components.

Write meaningful variable names.

Use TypeScript everywhere in the frontend.

Never use JavaScript unless required.

---

# UI Design Requirements

The UI should look like a modern AI SaaS application.

Design inspiration:

Apple

Vercel

Linear

Notion

Perplexity

Do NOT create a student-looking interface.

The interface should feel premium.

---

# Color Palette

Primary

#101916

Secondary

#355245

Accent

#648374

Surface

#AFC1B6

Background

#E3E5D8

Follow this palette consistently.

Never invent new primary colors.

---

# UI Principles

Minimal

Professional

Elegant

Premium

Modern

AI Inspired

Clean

Responsive

Accessible

Use consistent spacing.

Use rounded corners.

Use subtle shadows.

Use glassmorphism only where appropriate.

Do not overuse animations.

---

# Responsive Design

Support

Mobile

Tablet

Laptop

Desktop

Ultra-wide screens

Never break layouts.

---

# Typography

Use modern typography.

Good hierarchy.

Readable font sizes.

Proper spacing.

---

# Components

Create reusable components.

Examples

Button

Input

Card

Dialog

Modal

Table

Sidebar

Navbar

Footer

Toast

Alert

Loader

Skeleton

Charts

Upload Component

Prediction Card

Recommendation Card

Profile Card

Notification Card

History Table

Never duplicate components.

---

# Authentication

Use JWT Authentication.

Implement

Register

Login

Forgot Password

Reset Password

Logout

Protected Routes

Role-based Authentication

---

# User Roles

Farmer

Admin

Farmer permissions

Upload image

View prediction

View recommendations

View history

Update profile

Admin permissions

Manage users

View analytics

View logs

Monitor AI

Manage alerts

---

# Database

Database Engine

PostgreSQL

Use proper relationships.

Never denormalize unnecessarily.

Always use migrations.

Never hardcode IDs.

---

# REST APIs

Always follow the REST_API_SPEC.md.

Never rename endpoints.

Never rename JSON fields.

Never change request formats.

Never change response formats.

Backend implementation must strictly follow the API contract.

---



# AI Integration

GreenGuard uses three independent AI modules. Module 4 is the application-level report that shows their results together.

Module 1

Disease Detection

Purpose

• Disease Detection from one leaf photo (top-3 shortlist; may return status "uncertain" with prediction null)

Technology

CNN (live service, see ai/API_CONTRACT.md)

--------------------------------

Module 2

Soil & Nutrient Health

Purpose

• Nutrient risk levels from a farmer questionnaire

• pH / soil moisture / light comparison

• Overall soil health score and label

Technology

Machine Learning Model + Statistical Thresholding (live service, see REST_API_SPEC.md Section 8A)

--------------------------------

Module 3

Weather Risk

Purpose

• Temperature

• Humidity

• Rainfall

• Wind Speed

• Fungal Disease Risk

• Heat Stress Risk

• Drought Risk

Technology

Open-Meteo API + Rule Engine (local service at WEATHER_MODULE_URL)

--------------------------------

Module 4

Integrated Analysis Report (application layer — not an AI model, not a service)

Purpose

Store the Module 1, 2 and 3 results side by side (prediction_report = module1 / module2 / module3) and display each as its own section.

There is no Fusion model, no ANN and no Fusion API. Never invent a final diagnosis, combined confidence, score or recommendation.

The backend only consumes the module outputs.

It must never attempt to recreate AI predictions.
---

# AI Contract
# AI Contract

The AI team owns all machine learning models.

The backend must treat AI modules as external services.

Never modify AI outputs.

Never rename JSON fields.

Never calculate confidence scores.

Never infer predictions.

Never alter recommendation logic.

The backend only validates, stores, and forwards AI responses.

If the AI response changes, update REST_API_SPEC.md only after approval.

---

# File Upload

Accept

jpg

jpeg

png

Validate file size.

Generate preview.

Show upload progress.

Handle errors gracefully.

---

# Dashboard

Dashboard must include

• Welcome Banner

• Quick Scan

• Recent Predictions

• Weather Summary

• Recommendation Summary

• Prediction History

• Alerts

• Notifications

• Profile

• Recent Activity

• Soil Summary

• Crop Recommendation Summary

• Disease Statistics

---
# AI Communication Flow

Prediction Workflow

User uploads image

↓

Frontend sends request

↓

Django Backend

↓

Disease Detection Module (Module 1)

↓

Farm's latest Soil & Nutrient result (Module 2, stored — not called live)

↓

Weather Risk Module (Module 3)

↓

Backend stores prediction (Module 4 — Integrated Analysis Report)

↓

Backend returns JSON

↓

Frontend displays report

The backend is the only component allowed to communicate with AI services.

Frontend must never call AI APIs directly.

# Development Rules

Always build production-ready code.

Never create fake AI logic.

Never simulate prediction outputs unless Mock Mode is explicitly enabled.

Always use reusable components.

Always follow REST_API_SPEC.md.

Always follow PROJECT_SPECIFICATION.md.

Always follow ERD relationships.

Always follow the API JSON contracts exactly.

Never rename API endpoints.

Never rename JSON fields.

Never modify AI responses.

Never redesign the architecture without approval.

# Error Handling

Always show friendly error messages.

Never expose server errors.

Validate user input.

Handle network failures.

Show retry options.

---

# Loading States

Use skeleton loaders.

Use progress indicators.

Show AI processing state.

Show success state.

Show empty state.

---

# Notifications

Use toast notifications.

Examples

Login successful

Prediction completed

Upload successful

Profile updated

Error occurred

---

# Security

Hash passwords.

Validate all input.

Protect APIs.

Use JWT.

Prevent SQL Injection.

Prevent XSS.

Never expose secrets.

Use environment variables.

---

# Performance

Optimize images.

Lazy load components.

Code splitting.

Use Server Components where appropriate.

Minimize unnecessary re-renders.

Use caching where appropriate.

---

# Accessibility

Keyboard navigation.

ARIA labels.

Focus states.

Proper color contrast.

Semantic HTML.

---

# Code Quality

Write maintainable code.

Write readable code.

Use comments only where necessary.

Remove unused imports.

Avoid deeply nested components.

---

# Git Workflow

Commit after every completed module.

Example

Project Setup

Authentication

Database

Dashboard

Upload

Prediction

History

Alerts

Admin

Integration

---

# Documentation

Keep documentation updated.

README

REST API

Architecture

Database

Deployment

---

# Things Claude Must Never Do

Do not redesign the architecture.

Do not change the ERD.

Do not change database relationships.

Do not rename APIs.

Do not rename JSON fields.

Do not change AI contracts.

Do not use MongoDB.

Do not generate placeholder code without marking it clearly.

Do not hardcode API URLs.

Do not hardcode credentials.

Do not ignore responsiveness.

Do not create duplicate components.

---

# Development Workflow

Always complete modules in this order.

1. Project Setup

↓

2. Authentication

↓

3. PostgreSQL Database

↓

4. Frontend Layout

↓

5. Dashboard

↓

6. Image Upload

↓

7. Prediction Workflow

↓

8. Soil Analysis

↓

9. Weather Analysis

↓

10. Integrated Analysis Report (Module 4)

↓

11. Prediction History

↓

12. Recommendations

↓

13. Notifications

↓

14. Admin Dashboard

↓

15. AI Integration

↓

16. Testing

↓

17. Deployment

Never skip a module.

Every module must be fully functional before starting the next.

---
# Mock Development Mode

Before AI deployment is complete, the backend may use fixed mock JSON responses.

Mock responses must exactly match the JSON contracts defined in REST_API_SPEC.md.

Mock mode must be controlled by an environment variable.

ENABLE_MOCK_AI=true

Once AI deployment is complete, disabling Mock Mode should require no frontend changes.

# Expected Code Quality

The generated application must be suitable for

• Production Deployment

• Final Year Project Demonstration

• GitHub Portfolio

• AI Integration

• Cloud Deployment

• Future Mobile Application

The codebase must be

• Modular

• Scalable

• Secure

• Maintainable

• Responsive

• Accessible

• Well Documented

Every generated file should follow modern software engineering best practices.

# Documentation Priority

Always use the following documents as the source of truth, in order of priority:

1. docs/GREEN_GUARD_SYSTEM_SPECIFICATION_V2.md
2. docs/REST_API_SPEC.md
3. docs/DATABASE_SPECIFICATION.md
4. docs/UI_SPECIFICATION.md
5. docs/AI_MODULE_DELIVERY_SPECIFICATION.md

Do not modify APIs, database schema, or UI behavior unless explicitly instructed.

If implementation conflicts with the documentation, ask for clarification instead of making assumptions.
End of CLAUDE.md