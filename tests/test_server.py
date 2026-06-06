import sys
import os
# Ensure project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import json
from unittest.mock import patch
import server
print(f"DEBUG: server file is {server.__file__}")

@pytest.fixture(autouse=True)
def mock_auth():
    with patch('server._shared_check_access') as mock:
        mock.return_value = (True, "OK", "pro")
        yield mock

@pytest.fixture(autouse=True)
def reset_usage():
    server._usage = {}
    yield

class TestMDRClassification:
    def test_classify_pacemaker(self):
        result = server.classify_medical_device(query="Implantable pacemaker", api_key="test")
        assert result.risk_class == "Class III"
        assert "Rule 8" in result.rule_applied
        assert result.status == "active"

    def test_classify_spectacles(self):
        result = server.classify_medical_device(query="Prescription spectacles", api_key="test")
        assert result.risk_class == "Class I"
        assert result.rule_applied == "Rule 1"

    def test_classify_contact_lens(self):
        result = server.classify_medical_device(query="Daily contact lenses", api_key="test")
        assert result.risk_class == "Class IIb"

    def test_classify_hiv_test(self):
        result = server.classify_ivd(query="HIV rapid test kit", api_key="test")
        assert result.risk_class == "Class D"
        assert "Rule 1" in result.rule_applied

    def test_classify_pregnancy_test(self):
        result = server.classify_ivd(query="Digital pregnancy test", api_key="test")
        assert result.risk_class == "Class B"

    def test_samd_diagnostic_ai(self):
        result = server.samd_ai_ml_check(query="AI for diagnosing critical heart failure", api_key="test")
        assert "Class III" in result.risk_class
        assert "Rule 11(a)" in result.rule_applied

    def test_ce_marking_class_i(self):
        result = server.ce_marking_requirements(query="Hospital bed", api_key="test")
        assert result.notified_body_required is False
        assert "EU Declaration of Conformity" in result.requirements

    def test_ce_marking_class_iii(self):
        result = server.ce_marking_requirements(query="Heart valve", api_key="test")
        assert result.notified_body_required is True
        assert "Notified Body Audit & Certificate" in result.requirements

    def test_rate_limiting(self):
        server._usage["anonymous"] = []
        for _ in range(10):
            assert server._rl("free") is None
        assert "Free tier limit" in server._rl("free")

    def test_branding_presence(self):
        result = server.classify_medical_device(query="Stethoscope", api_key="test")
        assert "MEOK AI Labs" in result.branding
