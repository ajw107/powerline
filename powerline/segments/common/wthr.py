# vim:fileencoding=utf-8:noet
from __future__ import (unicode_literals, division, absolute_import, print_function)

import json

from powerline.lib.url import urllib_read, urllib_quote_plus
from powerline.lib.threaded import KwThreadedSegment
from powerline.segments import with_docstring


# XXX Warning: module name must not be equal to the segment name as long as this
# segment is imported into powerline.segments.common module.

weather_conditions_codes = {
	'✨': 'unknown',
	'☁️': 'cloudy',
	'🌫': 'foggy',
	'🌧': 'stormy',
	'❄️': 'snowy',
	'🌦': 'rainy',
	'🌨': 'snowy',
	'⛅️': 'cloudy',
	'☀️': 'sunny',
	'🌩': 'stormy',
	'⛈': 'stormy'
}

temp_conversions = {
	'C': lambda temp: temp,
	'F': lambda temp: (temp * 9 / 5) + 32,
	'K': lambda temp: temp + 273.15,
}

# Note: there are also unicode characters for units: ℃, ℉ and  K
temp_units = {
	'C': '°C',
	'F': '°F',
	'K': 'K',
}

class WeatherSegment(KwThreadedSegment):
	interval = 600
	default_location = None
	location_urls = {}

	@staticmethod
	def key(location_query=None, **kwargs):
		return location_query

	def get_request_url(self, location_query):
		try:
			return self.location_urls[location_query]
		except KeyError:
			if location_query is None:
				# Note: nekudo's api has also changed and is useless but wttr.in can use your ip address
				#TODO: change this to not use nekudo and use ip address of request to wwtr.in instead
				location_data = json.loads(urllib_read('http://geoip.nekudo.com/api/'))
				location = ','.join((
					location_data['city'],
					location_data['country']['name'],
					location_data['country']['code']
				))
				self.info('Location returned by nekudo is {0}', location)
			else:
				# Note: wttr.in will use your ip address if needed
				# Note: Also if specifiying location ONLY use city name
				# Note: (no idea how to get around cities with same name in different countires)
				location = location_query
			self.location_urls[location_query] = url = (
				'https://wttr.in/{0}?m&format={1}').format(urllib_quote_plus(location), urllib_quote_plus('%c+%t'))
			print(url)
			return url

	def compute_state(self, location_query):
		url = self.get_request_url(location_query)
		raw_response = urllib_read(url)
		if not raw_response:
			self.error('Failed to get response')
			return None

		split_response = raw_response.split('|')
		response = {
			'condition': split_response[0],
			'temp': split_response[1].rstrip('°C\n')[1:],
			'temp_multiplier': 1 if split_response[1].startswith('+') else -1
		}
		
		try:
			temp = float(response['temp']) * response['temp_multiplier']
			icon = response['condition']
		except (KeyError, ValueError):
			self.exception('Wttr.in returned malformed or unexpected response: {0}', repr(raw_response))
			return None

		return (temp, icon)

	def render_one(self, weather, icons=None, unit='C', temp_format=None, temp_coldest=-30, temp_hottest=40, **kwargs):
		if not weather:
			return None

		temp, icon = weather

		if icons and icon in weather_conditions_codes:
			icon = icons[weather_conditions_codes[icon]]

		temp_format = temp_format or ('{temp:.0f}' + temp_units[unit])
		converted_temp = temp_conversions[unit](temp)
		if temp <= temp_coldest:
			gradient_level = 0
		elif temp >= temp_hottest:
			gradient_level = 100
		else:
			gradient_level = (temp - temp_coldest) * 100.0 / (temp_hottest - temp_coldest)
		groups = ['weather_conditions', 'weather']
		return [
			{
				'contents': icon + ' ',
				'highlight_groups': groups,
				'divider_highlight_group': 'background:divider',
			},
			{
				'contents': temp_format.format(temp=converted_temp),
				'highlight_groups': ['weather_temp_gradient', 'weather_temp', 'weather'],
				'divider_highlight_group': 'background:divider',
				'gradient_level': gradient_level,
			},
		]


weather = with_docstring(WeatherSegment(),
'''Return weather from Wttr.in.

Uses GeoIP lookup from http://geoip.nekudo.com to automatically determine
your current location. This should be changed if you’re in a VPN or if your
IP address is registered at another location.

Returns a list of colorized icon and temperature segments depending on
weather conditions.

:param str unit:
	temperature unit, can be one of ``F``, ``C`` or ``K``
:param str location_query:
	location query for your current location, e.g. ``oslo, norway``
:param dict icons:
	dict for overriding default icons, e.g. ``{'heavy_snow' : u'❆'}``
:param str temp_format:
	format string, receives ``temp`` as an argument. Should also hold unit.
:param float temp_coldest:
	coldest temperature. Any temperature below it will have gradient level equal
	to zero.
:param float temp_hottest:
	hottest temperature. Any temperature above it will have gradient level equal
	to 100. Temperatures between ``temp_coldest`` and ``temp_hottest`` receive
	gradient level that indicates relative position in this interval
	(``100 * (cur-coldest) / (hottest-coldest)``).

Divider highlight group used: ``background:divider``.

Highlight groups used: ``weather_conditions`` or ``weather``, ``weather_temp_gradient`` (gradient) or ``weather``.
Also uses ``weather_conditions_{condition}`` for all weather conditions supported by Wttr.in.
''')
