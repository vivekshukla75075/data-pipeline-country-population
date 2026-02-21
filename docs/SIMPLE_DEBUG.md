# Simple Ingestion Debug - Step by Step

## The Problem

- Ingestion job shows "Succeeded"
- But no logs appear in CloudWatch
- And no data in S3 raw bucket

## Root Cause

**Logging parameters are NOT saved in the Glue job.**

The job runs but doesn't log because it's not configured to write logs to CloudWatch.

---

## CRITICAL FIX: Save Job Parameters

This is the most important step.

### Go to AWS Glue Console

1. **URL:** https://console.aws.amazon.com/glue/home
2. Click: **Jobs**
3. Click: **country-population-ingestion**
4. Click: **Edit job** button (top right)

### Add Job Parameters

⚠️ **IMPORTANT: Go to "Script" tab, NOT "Job details"**

1. Scroll down to bottom of page
2. Look for **"Job parameters"** section
3. You should see a button that says **"Add parameter"**
4. Click it THREE times and add:

