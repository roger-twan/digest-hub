"""Google Analytics 4 Data API Client."""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account


class GA4Client:
    """Client for fetching GA4 analytics data."""

    def __init__(self, property_id: Optional[str] = None, credentials_path: Optional[str] = None):
        """Initialize GA4 client.
        
        Args:
            property_id: GA4 property ID (e.g., '123456789')
            credentials_path: Path to service account JSON file
        """
        self.property_id = property_id or os.getenv('GA4_PROPERTY_ID')
        if not self.property_id:
            raise ValueError("GA4_PROPERTY_ID is required")
        
        # Handle credentials from environment variable (for GitHub Actions)
        creds_json = os.getenv('GA4_CREDENTIALS_JSON')
        if creds_json:
            credentials_info = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
        elif credentials_path:
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
        else:
            raise ValueError("Either GA4_CREDENTIALS_JSON or credentials_path is required")
        
        self.client = BetaAnalyticsDataClient(credentials=credentials)

    def get_daily_report(self, date: Optional[datetime] = None) -> Dict:
        """Fetch daily analytics report.
        
        Args:
            date: Date to fetch report for (defaults to yesterday)
            
        Returns:
            Dictionary with analytics data
        """
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        date_str = date.strftime('%Y-%m-%d')
        
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[
                Dimension(name="pageTitle"),
                Dimension(name="pagePath"),
            ],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="screenPageViews"),
                Metric(name="sessions"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
                Metric(name="newUsers"),
            ],
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
        )
        
        response = self.client.run_report(request)
        
        # Parse response into structured data
        data = {
            'date': date_str,
            'total_users': 0,
            'total_page_views': 0,
            'total_sessions': 0,
            'avg_session_duration': 0,
            'bounce_rate': 0,
            'new_users': 0,
            'top_pages': []
        }
        
        total_sessions_for_avg = 0
        
        for row in response.rows:
            page_title = row.dimension_values[0].value
            page_path = row.dimension_values[1].value
            
            active_users = int(row.metric_values[0].value)
            page_views = int(row.metric_values[1].value)
            sessions = int(row.metric_values[2].value)
            new_users = int(row.metric_values[5].value)
            
            data['total_users'] += active_users
            data['total_page_views'] += page_views
            data['total_sessions'] += sessions
            data['new_users'] += new_users
            total_sessions_for_avg += sessions
            
            data['top_pages'].append({
                'title': page_title,
                'path': page_path,
                'views': page_views,
                'users': active_users
            })
        
        # Calculate weighted averages
        if total_sessions_for_avg > 0:
            data['avg_session_duration'] = sum(
                float(r.metric_values[3].value) * int(r.metric_values[2].value)
                for r in response.rows
            ) / total_sessions_for_avg
        
        if data['total_sessions'] > 0:
            data['bounce_rate'] = sum(
                float(r.metric_values[4].value) * int(r.metric_values[2].value)
                for r in response.rows
            ) / data['total_sessions']
        
        # Sort top pages by views
        data['top_pages'] = sorted(data['top_pages'], key=lambda x: x['views'], reverse=True)[:10]
        
        # Fetch country data
        data['top_countries'] = self._get_top_countries(date_str, date_str)
        
        return data

    def _get_top_countries(self, start_date: str, end_date: str) -> List[Dict]:
        """Fetch top countries by users.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of country data dictionaries
        """
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[
                Dimension(name="country"),
            ],
            metrics=[
                Metric(name="activeUsers"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )
        
        response = self.client.run_report(request)
        
        countries = []
        for row in response.rows:
            country = row.dimension_values[0].value
            users = int(row.metric_values[0].value)
            countries.append({'country': country, 'users': users})
        
        # Sort by users and return top 10
        return sorted(countries, key=lambda x: x['users'], reverse=True)[:10]

    def get_weekly_report(self, end_date: Optional[datetime] = None) -> Dict:
        """Fetch weekly analytics report.
        
        Args:
            end_date: End date for the week (defaults to yesterday)
            
        Returns:
            Dictionary with weekly analytics data
        """
        if end_date is None:
            end_date = datetime.now() - timedelta(days=1)
        
        start_date = end_date - timedelta(days=6)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[
                Dimension(name="date"),
                Dimension(name="pageTitle"),
            ],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="screenPageViews"),
                Metric(name="sessions"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
                Metric(name="newUsers"),
            ],
            date_ranges=[DateRange(start_date=start_str, end_date=end_str)],
        )
        
        response = self.client.run_report(request)
        
        # Parse response
        data = {
            'start_date': start_str,
            'end_date': end_str,
            'total_users': 0,
            'total_page_views': 0,
            'total_sessions': 0,
            'avg_session_duration': 0,
            'bounce_rate': 0,
            'new_users': 0,
            'daily_breakdown': {},
            'top_pages': []
        }
        
        page_stats = {}
        total_sessions_for_avg = 0
        
        for row in response.rows:
            date = row.dimension_values[0].value
            page_title = row.dimension_values[1].value
            
            active_users = int(row.metric_values[0].value)
            page_views = int(row.metric_values[1].value)
            sessions = int(row.metric_values[2].value)
            new_users = int(row.metric_values[5].value)
            
            data['total_users'] += active_users
            data['total_page_views'] += page_views
            data['total_sessions'] += sessions
            data['new_users'] += new_users
            total_sessions_for_avg += sessions
            
            # Daily breakdown
            if date not in data['daily_breakdown']:
                data['daily_breakdown'][date] = {
                    'users': 0,
                    'page_views': 0,
                    'sessions': 0
                }
            data['daily_breakdown'][date]['users'] += active_users
            data['daily_breakdown'][date]['page_views'] += page_views
            data['daily_breakdown'][date]['sessions'] += sessions
            
            # Page stats
            if page_title not in page_stats:
                page_stats[page_title] = {'views': 0, 'users': 0}
            page_stats[page_title]['views'] += page_views
            page_stats[page_title]['users'] += active_users
        
        # Calculate weighted averages
        if total_sessions_for_avg > 0:
            data['avg_session_duration'] = sum(
                float(r.metric_values[3].value) * int(r.metric_values[2].value)
                for r in response.rows
            ) / total_sessions_for_avg
        
        if data['total_sessions'] > 0:
            data['bounce_rate'] = sum(
                float(r.metric_values[4].value) * int(r.metric_values[2].value)
                for r in response.rows
            ) / data['total_sessions']
        
        # Sort top pages
        data['top_pages'] = [
            {'title': title, 'views': stats['views'], 'users': stats['users']}
            for title, stats in sorted(page_stats.items(), key=lambda x: x[1]['views'], reverse=True)[:10]
        ]
        
        # Fetch country data (non-critical, so we catch errors)
        try:
            data['top_countries'] = self._get_top_countries(start_str, end_str)
        except Exception as e:
            print(f"Warning: Could not fetch country data: {e}")
            data['top_countries'] = []
        
        return data
