import asyncio
import httpx
import time
import random

# URL de tu API Gateway expuesta en AWS
URL = "https://kszuswykvl.execute-api.us-east-1.amazonaws.com/liquidaciones"

# Límite de concurrencia simultánea para saturar de forma controlada sin bloquear Windows
SEMAPHORE_LIMIT = 50 

async def send_request(client, payload, semaphore):
    async with semaphore:
        headers = {
            "Content-Type": "application/json"
        }
        try:
            response = await client.post(URL, json=payload, headers=headers, timeout=25.0)
            return response.status_code
        except httpx.TimeoutException:
            return "Timeout"
        except Exception as e:
            return str(e) or "ConnectionError"

async def main():
    total_requests = 50000
    print(f"🚀 Preparando lote de {total_requests} peticiones mixtas (Normales, Negativas, Duplicadas)...")
    
    
    # Distribución proporcional basada en el 100% (90% normales, 5% negativas, 5% duplicadas)
    num_normal = int(total_requests * 0.90)  # 45,000
    num_neg = int(total_requests * 0.05)     # 2,500
    num_dup = int(total_requests * 0.05)     # 2,500

    payloads = []

    # 1.  Peticiones normales y exitosas
    for i in range(num_normal):
        payloads.append({
            "id_liquidacion": f"liq-norm-{i}-{random.randint(100, 999)}",
            "id_productor": "prod-1043",
            "id_centro_acopio": "acopio-norte",
            "fecha_entrega": "2026-10-22",
            "producto": "Cacao Fino",
            "cantidad_kg": 400,
            "precio_kg": 1.27,
            "descuentos": 10.1
        })
        
    # 2. Peticiones con valores negativos (Para probar DLQ / Errores de negocio)
    for i in range(num_neg):
        payloads.append({
            "id_liquidacion": f"liq-neg-{i}-{random.randint(100, 999)}",
            "id_productor": "prod-1043",
            "id_centro_acopio": "acopio-norte",
            "fecha_entrega": "2026-10-22",
            "producto": "Cacao Fino",
            "cantidad_kg": -400,  # Valor negativo intencional
            "precio_kg": 1.27,
            "descuentos": 10.1
        })
        
    # 3. 50 Peticiones duplicadas (Para probar la Idempotencia / ConditionalCheckFailedException)
    # Se reutilizan 5 IDs base repetidas veces a lo largo del lote
    dup_ids = [f"liq-dup-target-{j}" for j in range(50)]
    for i in range(50):
        target_id = dup_ids[i % len(dup_ids)]
        payloads.append({
            "id_liquidacion": target_id,
            "id_productor": "prod-1043",
            "id_centro_acopio": "acopio-norte",
            "fecha_entrega": "2026-10-22",
            "producto": "Cacao Fino",
            "cantidad_kg": 400,
            "precio_kg": 1.27,
            "descuentos": 10.1
        })

    # Mezclar aleatoriamente el orden para simular un escenario real y caótico de producción
    print("🔀 Mezclando peticiones para simular tráfico concurrente real...")
    random.shuffle(payloads)

    print(f"🚀 Iniciando envío masivo de {total_requests} peticiones (Concurrencia: {SEMAPHORE_LIMIT})...")
    print("⏳ Esto puede tomar unos minutos debido al gran volumen. Por favor espera...")
    start_time = time.time()

    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
    limits = httpx.Limits(max_keepalive_connections=100, max_connections=200)

    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [send_request(client, p, semaphore) for p in payloads]
        results = await asyncio.gather(*tasks)

    end_time = time.time()
    total_time = end_time - start_time
    
    # Análisis de resultados
    success_count = results.count(202)
    print("\n========================================")
    print("📊 RESULTADOS DE LA PRUEBA DE 50K PETICIONES")
    print("========================================")
    print(f"⏱️ Tiempo total transcurrido: {total_time:.2f} segundos ({total_time / 60:.2f} minutos)")
    print(f"⚡ Peticiones por segundo: {total_requests / total_time:.2f} req/s")
    print(f"✅ Aceptadas por API Gateway (202): {success_count} / {total_requests}")


    other_results = {x: results.count(x) for x in set(results) if x != 202}
    if other_results:
        print(f"⚠️ Errores de red/timeout detectados: {other_results}")
    else:
        print("🎉 ¡Excelente! Todas las solicitudes de la prueba de 50k ingresaron perfectamente al búfer SQS.")
    print("========================================")

if __name__ == "__main__":
    asyncio.run(main())