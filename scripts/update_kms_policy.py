import json
import os

def main():
    src = '/tmp/key_policy.json'
    dst = '/tmp/key_policy_new.json'
    if not os.path.exists(src):
        print('No source key policy found at', src)
        return
    policy = json.load(open(src))
    sid = 'AllowLambdaRolesDecrypt'
    stmt = {
        'Sid': sid,
        'Effect': 'Allow',
        'Principal': {'AWS': []},
        'Action': [
            'kms:Decrypt',
            'kms:GenerateDataKey*',
            'kms:DescribeKey'
        ],
        'Resource': '*'
    }

    ing = os.environ.get('INGESTION_ROLE_ARN')
    notr = os.environ.get('NOTIFIER_ROLE_ARN')
    principals = []
    if ing and ing != 'None':
        principals.append(ing)
    if notr and notr != 'None':
        principals.append(notr)

    if principals:
        stmt['Principal']['AWS'] = principals if len(principals) > 1 else principals[0]
        # Check existing
        existing = [s for s in policy.get('Statement', []) if s.get('Sid') == sid]
        if not existing:
            policy.setdefault('Statement', []).append(stmt)
            print('Appended new statement to policy')
        else:
            existing_stmt = existing[0]
            old_principal = existing_stmt.get('Principal', {}).get('AWS')
            existing_stmt['Effect'] = 'Allow'
            existing_stmt['Principal'] = stmt['Principal']
            existing_stmt['Action'] = stmt['Action']
            existing_stmt['Resource'] = stmt['Resource']
            print(f'Updated existing statement principal from {old_principal} to {stmt['Principal']["AWS"]}')
        with open(dst, 'w') as f:
            json.dump(policy, f, indent=2)
    else:
        print('No principals found in environment; writing original policy to', dst)
        with open(dst, 'w') as f:
            json.dump(policy, f, indent=2)

if __name__ == '__main__':
    main()
