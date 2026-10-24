import asyncio
import httpx
import time
import random

# URL de tu API Gateway expuesta en AWS
URL = "https://kszuswykvl.execute-api.us-east-1.amazonaws.com/liquidaciones"

# Límite de concurrencia simultánea para no saturar los sockets de Windows
SEMAPHORE_LIMIT = 50 

async def send_request(client, index, semaphore):
    async with semaphore:
        payload = {
            "id_liquidacion": f"liq-load-{index}-{random.randint(100, 999)}",
            "id_productor": "prod-1043",
            "id_centro_acopio": "acopio-norte",
            "fecha_entrega": "2026-10-22",
            "producto": "Cacao Fino",
            "cantidad_kg": 400,
            "precio_kg": 1.27,
            "descuentos": 10.1
        }
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = await client.post(URL, json=payload, headers=headers, timeout=20.0)
            return response.status_code
        except httpx.TimeoutException:
            return "Timeout"
        except Exception as e:
            return str(e) or "ConnectionError"

async def main():
    total_requests = 1000
    print(f"🚀 Iniciando prueba controlada: enviando {total_requests} peticiones (concurrencia de {SEMAPHORE_LIMIT})...")
    start_time = time.time()

    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
    
    # Configuramos un cliente HTTP con límites estables de conexiones
    limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
    
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [send_request(client, i, semaphore) for i in range(total_requests)]
        results = await asyncio.gather(*tasks)

    end_time = time.time()
    total_time = end_time - start_time
    
    # Análisis de resultados
    success_count = results.count(202)
    print("\n========================================")
    print("📊 RESULTADOS DE LA PRUEBA DE CARGA")
    print("========================================")
    print(f"⏱️ Tiempo total transcurrido: {total_time:.2f} segundos")
    print(f"⚡ Peticiones por segundo: {total_requests / total_time:.2f} req/s")
    print(f"✅ Peticiones exitosas (202 Accepted): {success_count} / {total_requests}")
    
    other_results = {x: results.count(x) for x in set(results) if x != 202}
    if other_results:
        print(f"⚠️ Errores detectados: {other_results}")
    else:
        print("🎉 ¡Excelente! Todas las peticiones fueron procesadas con éxito por API Gateway.")
    print("========================================")

if __name__ == "__main__":
    asyncio.run(main())