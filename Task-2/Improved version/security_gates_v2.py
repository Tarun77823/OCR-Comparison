# security_gates_v2.py
from common_infra_v2 import Dependencies, deps_ok_for, OP_TIER

OPS = [
    "view_public", "view_profile_basic", "low_value_action",
    "view_pii", "export_data", "change_permissions",
    "high_value_action", "issue_token", "rotate_keys", "transfer",
]

def run(name: str, deps: Dependencies):
    print(f"\n Scenario: {name} ")
    print(deps)
    for op in OPS:
        ok, reason = deps_ok_for(op, deps)
        print(f"{op:20} -> {ok} | {reason} | tier={OP_TIER.get(op, 'TIER_2')}")

def main():
    run("All healthy", Dependencies())
    run("Policy down", Dependencies(policy_ok=False))
    run("Risk down", Dependencies(risk_ok=False))
    run("Audit down", Dependencies(audit_ok=False))
    run("KMS down", Dependencies(kms_ok=False))
    run("Auth down", Dependencies(auth_ok=False))

if __name__ == "__main__":
    main()
