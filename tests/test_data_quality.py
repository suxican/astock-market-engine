"""数据质量层测试"""
import pytest


class TestDataSource:
    def test_source_confidence_ordering(self):
        from backend.services.data_quality import DataSource, SOURCE_CONFIDENCE
        assert SOURCE_CONFIDENCE[DataSource.SINA] > SOURCE_CONFIDENCE[DataSource.AKSHARE]
        assert SOURCE_CONFIDENCE[DataSource.AKSHARE] > SOURCE_CONFIDENCE[DataSource.MOCK]
        assert SOURCE_CONFIDENCE[DataSource.MOCK] > SOURCE_CONFIDENCE[DataSource.DEFAULT]


class TestDataQuality:
    def test_is_valid(self):
        from backend.services.data_quality import DataQuality, DataSource
        q = DataQuality(source=DataSource.SINA)
        assert q.is_valid() is True
        assert q.is_mock() is False

    def test_mock_not_valid(self):
        from backend.services.data_quality import DataQuality, DataSource
        q = DataQuality(source=DataSource.MOCK)
        assert q.is_valid() is False
        assert q.is_mock() is True

    def test_to_dict(self):
        from backend.services.data_quality import DataQuality, DataSource
        q = DataQuality(source=DataSource.TENCENT)
        d = q.to_dict()
        assert "source" in d
        assert "confidence" in d
        assert "realtime" in d


class TestClassifyStatus:
    def test_realtime(self):
        from backend.services.data_quality import DataQuality, DataSource, classify_system_status
        q = DataQuality(source=DataSource.SINA, realtime=True)
        assert classify_system_status(q) == "realtime"

    def test_mock_status(self):
        from backend.services.data_quality import DataQuality, DataSource, classify_system_status
        q = DataQuality(source=DataSource.MOCK)
        assert classify_system_status(q) == "mock"

    def test_none_status(self):
        from backend.services.data_quality import classify_system_status
        assert classify_system_status(None) == "unknown"
