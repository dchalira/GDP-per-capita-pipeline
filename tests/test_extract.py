import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from app.load import fetch_data, fetch_indicator # Point to load.py if combined

class TestExtract(unittest.TestCase):
    @patch('app.load.requests.Session')
    def test_fetch_indicator_success(self, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {},  # metadata
            [
                {
                    'country': {'value': 'USA'},
                    'date': '2020',
                    'value': 60000.0
                }
            ]
        ]
        mock_session.return_value.get.return_value = mock_response

        # Matches the updated column name used in your fetch_data()
        result = fetch_indicator("NY.GDP.PCAP.CD", "gdp_per_capita")
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['country'], 'USA')
        self.assertEqual(result.iloc[0]['year'], 2020)
        self.assertEqual(result.iloc[0]['gdp_per_capita'], 60000.0)

    @patch('app.load.requests.Session')
    def test_fetch_indicator_failure(self, mock_session):
        mock_session.return_value.get.side_effect = Exception("Network error")

        result = fetch_indicator("NY.GDP.PCAP.CD", "gdp_per_capita")
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 0)

    @patch('app.load.fetch_indicator')
    def test_fetch_data_success(self, mock_fetch):
        # Now we only mock the ONE dataframe the current pipeline expects
        mock_gdp_pc = pd.DataFrame([{'country': 'USA', 'year': 2020, 'gdp_per_capita': 60000}])
        
        mock_fetch.return_value = mock_gdp_pc

        result = fetch_data()
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertIn('source', result.columns)
        self.assertIn('gdp_per_capita', result.columns)
        # Removed HIV, life expectancy, and generic gdp assertions
        
if __name__ == '__main__':
    unittest.main()