import asyncio
import httpx
import time
import random

URL = "https://example.execute-api.us-east-1.amazonaws.com/liquidaciones"

TOTAL_REQUESTS = 1000      # Número total de peticiones
REQUEST_DELAY = 2.0        # Segundos exactos de espera entre cada petición

# Lista para almacenar IDs generados previamente y poder reutilizarlos en los duplicados
generated_ids = []

def generate_payload(index):
    # Se ajustan las opciones y pesos: % normal, % duplicado, % negativo
    tipo = random.choices(["normal", "duplicado", "negativo"], weights=[0.70, 0.01, 0.29])[0]
    
    if tipo == "normal":
        id_liq = f"liq-norm-{index}-{random.randint(100, 999)}"
        generated_ids.append(id_liq)
        payload = {
            "id_liquidacion": id_liq,
            "id_productor": "prod-1043",
            "id_centro_acopio": "acopio-norte",
            "fecha_entrega": "2026-10-22",
            "producto": "Cacao Fino",
            "cantidad_kg": round(random.uniform(100, 500), 2),
            "precio_kg": round(random.uniform(1.0, 3.0), 2),
            "descuentos": round(random.uniform(0.0, 15.0), 2)
        }
    elif tipo == "duplicado":
        # Si ya existen IDs previos, selecciona uno al azar; de lo contrario, crea uno base
        if generated_ids:
            id_liq = random.choice(generated_ids)
        else:
            id_liq = f"liq-dup-base-{index}"
            generated_ids.append(id_liq)
            
        payload = {
            "id_liquidacion": id_liq,  # ID repetido intencionalmente
            "id_productor": "prod-1043",
            "id_centro_acopio": "acopio-norte",
            "fecha_entrega": "2026-10-22",
            "producto": "Cacao Fino",
            "cantidad_kg": round(random.uniform(100, 500), 2),
            "precio_kg": round(random.uniform(1.0, 3.0), 2),
            "descuentos": round(random.uniform(0.0, 15.0), 2)
        }
    else:  # "negativo"
        id_liq = f"liq-neg-{index}"
        generated_ids.append(id_liq)
        payload = {
            "id_liquidacion": id_liq,
            "id_productor": "prod-1043",
            "id_centro_acopio": "acopio-norte",
            "fecha_entrega": "2026-10-22",
            "producto": "Cacao Fino",
            "cantidad_kg": -random.randint(10, 500),
            "precio_kg": -round(random.uniform(0.5, 5.0), 2),
            "descuentos": -5.0
        }
    
    return tipo, payload

async def main():
    print(f" Iniciando envío secuencial de {TOTAL_REQUESTS} peticiones (1 cada {REQUEST_DELAY} segundos)...\n")
    start_time = time.time()
    
    results = []
    
    async with httpx.AsyncClient() as client:
        for i in range(TOTAL_REQUESTS):
            index = i + 1
            tipo, payload = generate_payload(index)
            headers = {"Content-Type": "application/json"}
            
            try:
                response = await client.post(URL, json=payload, headers=headers, timeout=20.0)
                resultado = response.status_code
            except httpx.TimeoutException:
                resultado = "Timeout"
            except Exception as e:
                resultado = str(e) or "ConnectionError"
                
            print(f"Petición {index} [{tipo}] -> Resultado: {resultado}")
            results.append(resultado)
            
            # Espera 2 segundos exactos ANTES de pasar a la siguiente petición (excepto en la última)
            if index < TOTAL_REQUESTS:
                await asyncio.sleep(REQUEST_DELAY)

    end_time = time.time()
    total_time = end_time - start_time
    
    # Análisis final de resultados
    print("RESULTADOS FINALES DE LA PRUEBA")
    print(f"Tiempo total transcurrido: {total_time:.2f} segundos")
    
    unique_results = set(results)
    for code in sorted(unique_results, key=lambda x: str(x) if isinstance(x, int) else str(x)):
        count = results.count(code)
        print(f"• Respuesta '{code}': {count} peticiones")

if __name__ == "__main__":
    asyncio.run(main())