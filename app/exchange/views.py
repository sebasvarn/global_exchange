
import json
import os
import requests
from django.http import JsonResponse
from django.conf import settings
from django.views import View


class ExchangeRatesView(View):
	def get(self, request):
		"""
		Permite elegir la fuente de datos:
		- ?source=api para consumir la API externa
		- ?source=local (o sin parámetro) para usar el mock local
		"""
		source = request.GET.get('source', 'api')

		if source == 'api':
			# --- CONSUMO DE API EXTERNA ---
			# Descomenta el bloque siguiente y asegúrate de tener requests instalado
			
			try:
				url = "http://localhost:9000/api/rates/latest"  # Cambia por la API real
				response = requests.get(url)
				response.raise_for_status()
				data = response.json()
			except Exception as e:
				return JsonResponse({'error': str(e)}, status=500)
			return JsonResponse({'rates': data})
			#
			# Por ahora, responde con un mensaje de ejemplo:
		# return JsonResponse({'info': 'Aquí iría la respuesta de la API externa. Descomenta el bloque correspondiente para activarlo.'})

		# --- MODO LOCAL: LEE EL MOCK JSON ---
		# json_path = os.path.join(settings.BASE_DIR, 'exchange', 'mock_data', 'mock_exchange_rates.json')
		# try:
		# 	with open(json_path, 'r', encoding='utf-8') as f:
		# 		data = json.load(f)
		# except Exception as e:
		# 	return JsonResponse({'error': str(e)}, status=500)
		# return JsonResponse({'rates': data})


