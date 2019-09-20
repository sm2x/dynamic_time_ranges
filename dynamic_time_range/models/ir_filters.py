# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta as relativedelta
from pytz import timezone
from odoo.exceptions import UserError

# KNOWN ISSUES:
# 1- Language is fetched from user sent in vals; this could not always be correct (create_or_replace is context-blind).
# 2- Timezone conversion not always exact. Needs more testing.


class Filter(models.Model):
    _inherit = 'ir.filters'

    @api.model
    @api.returns('self', lambda value: value.id)
    def create_or_replace(self, vals):
        def get_time_range():
            try:
                return vals['context']['timeRangeMenuData']['timeRange']
            except KeyError:
                return False

        def get_comparison_range():
            try:
                return vals['context']['timeRangeMenuData']['comparisonTimeRange']
            except KeyError:
                return False
        lang = self.env['res.users'].browse(vals['user_id']).lang
        translated_terms = self.env['ir.translation'].search([
            '&',
                ('name', '=', 'addons/web/static/src/js/views/search/time_range_menu_options.js'),
                ('lang', '=', lang)])
        _ = {tr.value: tr.source for tr in translated_terms}

        time_range = get_time_range()
        if time_range:
            op = _.get(vals['context']['timeRangeMenuData']['timeRangeDescription'], 'Last 30 Days')
            field = time_range[1][0]
            vals['context']['timeRangeMenuData']['timeRange'] = op
            vals['context']['timeRangeMenuData']['field'] = field

        comparison_range = get_comparison_range()
        if comparison_range:
            comp_op = _.get(vals['context']['timeRangeMenuData']['comparisonTimeRangeDescription'])
            vals['context']['timeRangeMenuData']['comparisonTimeRange'] = comp_op
        return super(Filter, self).create_or_replace(vals)

    @api.model
    def get_filters(self, model, action_id=None):
        res = super(Filter, self).get_filters(model, action_id)
        for filt in res:
            if 'context' in filt:
                eval_context = eval(filt['context'])
                if 'timeRangeMenuData' in eval_context:
                    if 'timeRange' in eval_context['timeRangeMenuData']:
                        time_range = eval_context['timeRangeMenuData']['timeRange']
                        comparsion_time_range = eval_context['timeRangeMenuData']['comparisonTimeRange'] or None
                        field = eval_context['timeRangeMenuData']['field']
                        if time_range == 'Last 7 Days':
                            time_domain, comparison_domain = self.simple_past_delta(7, field, comparison=comparsion_time_range)
                        elif time_range == 'Last 30 Days':
                            time_domain, comparison_domain = self.simple_past_delta(30, field, comparison=comparsion_time_range)
                        elif time_range == 'Last 365 Days':
                            time_domain, comparison_domain = self.simple_past_delta(365, field, comparison=comparsion_time_range)

                        elif time_range == 'Today':
                            time_domain, comparison_domain = self.day(field, comparison=comparsion_time_range)
                        elif time_range == 'This Week':
                            time_domain, comparison_domain = self.week(field, comparison=comparsion_time_range)
                        elif time_range == 'This Month':
                            time_domain, comparison_domain = self.month(field, comparison=comparsion_time_range)
                        elif time_range == 'This Tremester':
                            time_domain, comparison_domain = self.tremester(field, comparison=comparsion_time_range)
                        elif time_range == 'This Year':
                            time_domain, comparison_domain = self.year(field, comparison=comparsion_time_range)

                        elif time_range == 'Yesterday':
                            time_domain, comparison_domain = self.day(field, last=True, comparison=comparsion_time_range)
                        elif time_range == 'Last Week':
                            time_domain, comparison_domain = self.week(field, last=True, comparison=comparsion_time_range)
                        elif time_range == 'Last Month':
                            time_domain, comparison_domain = self.month(field, last=True, comparison=comparsion_time_range)
                        elif time_range == 'Last Trimester':
                            time_domain, comparison_domain = self.tremester(field, last=True, comparison=comparsion_time_range)
                        elif time_range == 'Last Year':
                            time_domain, comparison_domain = self.year(field, last=True, comparison=comparsion_time_range)
                        else:
                            raise UserError("Unrecognized operation: %s" % time_range)
                        eval_context['timeRangeMenuData']['timeRange'] = time_domain
                        if comparison_domain:
                            eval_context['timeRangeMenuData']['comparisonTimeRange'] = comparison_domain
                    filt['context'] = repr(eval_context)
        return res

    def simple_past_delta(self, nb_of_days, field, comparison=None):
        today = datetime.combine(datetime.today(), time(0,0,0))
        past = today - relativedelta(days=nb_of_days)
        time_domain = self.make_domain(field, past, today)
        if comparison:
            if comparison == 'Previous Year':
                today -= relativedelta(years=1)
                past -= relativedelta(years=1)
            elif comparison == 'Previous Period':
                today -= relativedelta(days=nb_of_days)
                past -= relativedelta(days=nb_of_days)
            comparison_domain = self.make_domain(field, past, today)
        else:
            comparison_domain = None
        return time_domain, comparison_domain

    def day(self, field, last=False, comparison=None):
        start = datetime.combine(datetime.today(), time(0, 0, 0))
        end = start + relativedelta(days=1)
        if last:
            start -= relativedelta(days=1)
            end -= relativedelta(days=1)
        time_domain = self.make_domain(field, start, end)
        if comparison:
            if comparison == 'Previous Year':
                start -= relativedelta(years=1)
                end -= relativedelta(years=1)
            elif comparison == 'Previous Period':
                start -= relativedelta(days=1)
                end -= relativedelta(days=1)
            comparison_domain = self.make_domain(field, start, end)
        else:
            comparison_domain = None
        return time_domain, comparison_domain

    def week(self, field, last=False, comparison=None):
        start = datetime.today() - relativedelta(days=datetime.today().weekday())
        start = datetime.combine(start, time(0,0,0))
        end = start + relativedelta(days=7)
        if last:
            start -= relativedelta(weeks=1)
            end -= relativedelta(weeks=1)
        time_domain = self.make_domain(field, start, end)
        if comparison:
            if comparison == 'Previous Year':
                start -= relativedelta(years=1)
                end -= relativedelta(years=1)
            elif comparison == 'Previous Period':
                start -= relativedelta(days=7)
                end -= relativedelta(days=7)
            comparison_domain = self.make_domain(field, start, end)
        else:
            comparison_domain = None
        return time_domain, comparison_domain

    def month(self, field, last=False, comparison=None):
        start = datetime(year=datetime.today().year, month=datetime.today().month, day=1, hour=0, minute=0, second=0)
        end = start + relativedelta(months=1)
        if last:
            start -= relativedelta(months=1)
            end -= relativedelta(months=1)
        time_domain = self.make_domain(field, start, end)
        if comparison:
            if comparison == 'Previous Year':
                start -= relativedelta(years=1)
                end -= relativedelta(years=1)
            elif comparison == 'Previous Period':
                start -= relativedelta(months=1)
                end -= relativedelta(months=1)
            comparison_domain = self.make_domain(field, start, end)
        else:
            comparison_domain = None
        return time_domain, comparison_domain

    def tremester(self, field, last=False, comparison=None):
        start_month = datetime.today().month // 3
        start = datetime(year=datetime.today().year, month=start_month, day=1, hour=0, minute=0, second=0)
        end = start + relativedelta(months=3)
        if last:
            start -= relativedelta(months=3)
            end -= relativedelta(months=3)
        time_domain = self.make_domain(field, start, end)
        if comparison:
            if comparison == 'Previous Year':
                start -= relativedelta(years=1)
                end -= relativedelta(years=1)
            elif comparison == 'Previous Period':
                start -= relativedelta(months=3)
                end -= relativedelta(months=3)
            comparison_domain = self.make_domain(field, start, end)
        else:
            comparison_domain = None
        return time_domain, comparison_domain

    def year(self, field, last=False, comparison=None):
        start = datetime(year=datetime.today().year, month=1, day=1, hour=0, minute=0, second=0)
        end = start + relativedelta(years=1)
        if last:
            start -= relativedelta(years=1)
            end -= relativedelta(years=1)
        time_domain = self.make_domain(field, start, end)
        if comparison:
            start -= relativedelta(years=1)
            end -= relativedelta(years=1)
            comparison_domain = self.make_domain(field, start, end)
        else:
            comparison_domain = None
        return time_domain, comparison_domain

    def make_domain(self, field, start, end):
        tz = timezone(self.env.context.get('tz', 'UTC'))
        start_str = start.replace(tzinfo=tz).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        end_str = end.replace(tzinfo=tz).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        return ['&', (field, '>=', start_str), (field, '<', end_str)]
