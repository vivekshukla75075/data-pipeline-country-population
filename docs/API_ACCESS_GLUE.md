# Enable API Access in AWS Glue Jobs

## Problem

API calls fail with 400 errors in Glue, but work locally. This is because:
- Glue jobs run in a VPC by default
- They can't access external APIs without NAT Gateway
- Network connectivity is restricted

## Solution: Add NAT Gateway to Glue Job

### Option 1: Disable VPC (Easiest - for Development)

1. Go to **AWS Glue → Jobs → country-population-ingestion**
2. Click **Edit job**
3. Go to **Job details** tab
4. Scroll to **Network section**
5. Under "Python library path", look for **VPC** option
6. **Remove VPC** (or set to "No VPC")
7. Click **Save**

**This allows your job to access external APIs.**

### Option 2: Add NAT Gateway (Production)

If you need VPC for security:

1. **Create NAT Gateway:**
   ```bash
   # Get public subnet ID
   aws ec2 describe-subnets --query 'Subnets[0].SubnetId' --output text
   
   # Create Elastic IP
   aws ec2 allocate-address --domain vpc
   
   # Create NAT Gateway
   aws ec2 create-nat-gateway --subnet-id <SUBNET_ID> --allocation-id <ALLOCATION_ID>
   ```

2. **Update Route Table:**
   ```bash
   aws ec2 create-route --route-table-id <ROUTE_TABLE_ID> \
     --destination-cidr-block 0.0.0.0/0 \
     --nat-gateway-id <NAT_GATEWAY_ID>
   ```

3. **Update Glue Job VPC Configuration:**
   - Go to Glue job → Edit job → Job details
   - Set VPC to your VPC with NAT Gateway
   - Click **Save**

---

## Quick Fix for Development

**Just disable VPC - this is the fastest way:**

1. **Edit job in console**
2. **Remove VPC setting**
3. **Save**
4. **Run job again**

The API should now work!

---

## Verify API is Working

Run job and check:

```bash
# Check logs
aws s3 ls s3://data-pipeline-country-population/logs/ingestion/

# View latest log
aws s3 cp s3://data-pipeline-country-population/logs/ingestion/success_YYYYMMDD_HHMMSS.log - | cat
```

Should show:
