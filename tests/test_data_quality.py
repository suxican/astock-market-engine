"""数据质量层测试"""


class TestDataSource:
    def test_source_confidence_ordering(self):
        from backend.services.data_quality import SOURCE_CONFIDENCE, DataSource
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

    def test_empty_dataframe_keeps_quality_attrs(self):
        import pandas as pd
        from backend.services.data_quality import DataSource, tag_kline_df

        df = tag_kline_df(pd.DataFrame(), DataSource.MOCK, fallback_used=True)

        assert df.empty
        assert df.attrs["_quality"].source == DataSource.MOCK
        assert df.attrs["_fallback_used"] is True


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


class TestFlowDataQuality:
    def test_stock_fund_flow_failure_returns_deterministic_empty(self, monkeypatch):
        from backend.services import flow_data

        monkeypatch.setattr(flow_data, "_try_akshare", lambda *args, **kwargs: None)

        result = flow_data.get_stock_fund_flow("600519")

        assert result["主力净流入"] == 0.0
        assert result["data_available"] is False
        assert result["_quality"]["source"] == "default"

    def test_sector_type_alias_uses_current_akshare_name(self, monkeypatch):
        import pandas as pd
        from backend.services import flow_data

        calls = {}

        def fake_try_akshare(func, default_return, *args, **kwargs):
            calls["sector_type"] = kwargs["sector_type"]
            return pd.DataFrame({"名称": ["半导体"], "主力净流入-净额": [1.0]})

        monkeypatch.setattr(flow_data, "_cache_get", lambda key: None)
        monkeypatch.setattr(flow_data, "_cache_set", lambda *args, **kwargs: None)
        monkeypatch.setattr(flow_data, "_try_akshare", fake_try_akshare)

        df = flow_data.get_sector_fund_flow_by_type("行业资金流向")

        assert calls["sector_type"] == "行业资金流"
        assert len(df) == 1
        assert df.attrs["_quality"].source.value == "akshare"

    def test_sector_flow_uses_curl_fallback_when_akshare_empty(self, monkeypatch):
        import pandas as pd
        from backend.services import flow_data

        monkeypatch.setattr(flow_data, "_cache_get", lambda key: None)
        monkeypatch.setattr(flow_data, "_cache_set", lambda *args, **kwargs: None)
        monkeypatch.setattr(flow_data, "_try_akshare", lambda *args, **kwargs: pd.DataFrame())
        monkeypatch.setattr(
            flow_data,
            "_fetch_sector_fund_flow_curl",
            lambda sector_type: pd.DataFrame({"名称": ["半导体"], "主力净流入-净额": [1.0]}),
        )

        df = flow_data.get_sector_fund_flow_by_type("行业资金流")

        assert len(df) == 1
        assert df.attrs["_quality"].source.value == "curl_eastmoney"
        assert df.attrs["_fallback_used"] is True


class TestLimitPoolCrossCheck:
    def test_cross_check_marks_warning_on_large_count_gap(self, monkeypatch):
        import pandas as pd
        from backend.services import limit_data

        pool = pd.DataFrame({"代码": ["000001", "000002", "000003"]})
        spot = pd.DataFrame({"涨跌幅": [10.0]})

        monkeypatch.setattr("backend.services.quote_data._get_spot_em_df", lambda: spot)

        checked = limit_data._attach_spot_cross_check(pool, "up")

        assert checked.attrs["_cross_check"]["enabled"] is True
        assert checked.attrs["_cross_check"]["pool_count"] == 3
        assert checked.attrs["_cross_check"]["spot_count"] == 1
        assert checked.attrs["_cross_check"]["status"] == "warning"
