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
            json.dump(policy, open(dst, 'w'), indent=2)
            print('Appended new statement to policy')
        else:
            print('Statement already exists; writing existing policy to', dst)
            json.dump(policy, open(dst, 'w'), indent=2)
    else:
        print('No principals found in environment; writing original policy to', dst)
        json.dump(policy, open(dst, 'w'), indent=2)

if __name__ == '__main__':
    main()
