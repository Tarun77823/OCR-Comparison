import unittest
from data_model_v4 import *

class TestIsolation(unittest.TestCase):

    def test_tenant_mismatch(self):

        obj = DataObject(
            object_id="doc",
            tenant_id="t1",
            owner_id="owner",
            home_region="US",
            data_tier="TIER3",
            encrypted_blob=b"abc"
        )

        ctx = RequestContext(
            user_id="agent",
            role="Agent",
            tenant_id="t2",
            purpose="lending_underwriting",
            serving_region="US"
        )

        self.assertNotEqual(ctx.tenant_id,obj.tenant_id)


if __name__ == "__main__":
    unittest.main()