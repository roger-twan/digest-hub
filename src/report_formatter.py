"""Shared analytics report formatting for notification channels."""

from datetime import datetime
from typing import Dict


class ReportFormatter:
    bold = "*"

    def format_daily_report(self, data: Dict) -> str:
        """Format daily analytics data as a notification message.
        
        Args:
            data: Daily analytics data dictionary
            
        Returns:
            Formatted message string
        """
        date = data.get('date', 'Unknown')
        
        # Format duration
        avg_duration = data.get('avg_session_duration', 0)
        minutes = int(avg_duration // 60)
        seconds = int(avg_duration % 60)
        duration_str = f"{minutes}m {seconds}s"
        
        # Format bounce rate
        bounce_rate = data.get('bounce_rate', 0)
        bounce_rate_str = f"{bounce_rate * 100:.1f}%"
        
        message = f"""📊 {self.bold}Daily Analytics Report - {date}{self.bold}

{self.bold}📈 Overview{self.bold}
• Total Users: `{data.get('total_users', 0):,}`
• New Users: `{data.get('new_users', 0):,}`
• Sessions: `{data.get('total_sessions', 0):,}`
• Page Views: `{data.get('total_page_views', 0):,}`

{self.bold}🔍 Engagement{self.bold}
• Avg Session Duration: `{duration_str}`
• Bounce Rate: `{bounce_rate_str}`

{self.bold}🌍 Top Countries{self.bold}"""

        for i, country in enumerate(data.get('top_countries', [])[:5], 1):
            country_name = country.get('country', 'Unknown')[:20]
            users = country.get('users', 0)
            message += f"\n{i}. {country_name} - `{users:,}` users"
        
        message += f"\n\n{self.bold}🔥 Top Pages{self.bold}"
        
        for i, page in enumerate(data.get('top_pages', [])[:5], 1):
            title = page.get('title', 'Unknown')[:30]
            views = page.get('views', 0)
            message += f"\n{i}. {title}... - `{views:,}` views"
        
        return message

    def format_weekly_report(self, data: Dict) -> str:
        """Format weekly analytics data as a notification message.
        
        Args:
            data: Weekly analytics data dictionary
            
        Returns:
            Formatted message string
        """
        start_date = data.get('start_date', 'Unknown')
        end_date = data.get('end_date', 'Unknown')
        
        # Format duration
        avg_duration = data.get('avg_session_duration', 0)
        minutes = int(avg_duration // 60)
        seconds = int(avg_duration % 60)
        duration_str = f"{minutes}m {seconds}s"
        
        # Format bounce rate
        bounce_rate = data.get('bounce_rate', 0)
        bounce_rate_str = f"{bounce_rate * 100:.1f}%"
        
        message = f"""📊 {self.bold}Weekly Analytics Report{self.bold}
{self.bold}{start_date} - {end_date}{self.bold}

{self.bold}📈 Overview{self.bold}
• Total Users: `{data.get('total_users', 0):,}`
• New Users: `{data.get('new_users', 0):,}`
• Sessions: `{data.get('total_sessions', 0):,}`
• Page Views: `{data.get('total_page_views', 0):,}`

{self.bold}🔍 Engagement{self.bold}
• Avg Session Duration: `{duration_str}`
• Bounce Rate: `{bounce_rate_str}`

{self.bold}📅 Daily Breakdown{self.bold}"""

        # Sort daily breakdown by date
        daily = data.get('daily_breakdown', {})
        for date in sorted(daily.keys()):
            day_data = daily[date]
            formatted_date = datetime.strptime(date, '%Y%m%d').strftime('%a %m/%d')
            message += f"\n• {formatted_date}: `{day_data['users']:,}` users, `{day_data['page_views']:,}` views"
        
        message += f"\n\n{self.bold}🌍 Top Countries This Week{self.bold}"
        for i, country in enumerate(data.get('top_countries', [])[:5], 1):
            country_name = country.get('country', 'Unknown')[:20]
            users = country.get('users', 0)
            message += f"\n{i}. {country_name} - `{users:,}` users"
        
        message += f"\n\n{self.bold}🔥 Top Pages This Week{self.bold}"
        for i, page in enumerate(data.get('top_pages', [])[:5], 1):
            title = page.get('title', 'Unknown')[:30]
            views = page.get('views', 0)
            message += f"\n{i}. {title}... - `{views:,}` views"
        
        return message

