const { SQSClient, SendMessageCommand } = require("@aws-sdk/client-sqs");
const sqs = new SQSClient({});

outputs = {};
exports.handler = async (event) => {
    try {
        if (!event.body) {
            return { statusCode: 400, body: JSON.stringify({ error: "Cuerpo de solicitud vacío" }) };
        }

        const data = JSON.parse(event.body);
        
        // Validación básica de campos requeridos según el diccionario de datos
        const requiredFields = ["id_liquidacion", "id_productor", "id_centro_acopio", "fecha_entrega", "producto", "cantidad_kg", "precio_kg", "descuentos"];
        for (let field of requiredFields) {
            if (data[field] === undefined) {
                return { statusCode: 400, body: JSON.stringify({ error: `Falta el campo obligatorio: ${field}` }) };
            }
        }

        const params = {
            QueueUrl: process.env.QUEUE_URL,
            MessageBody: JSON.stringify({
                ...data,
                estado: "recibido",
                intentos_entrega: 0,
                fecha_procesamiento: new Date().toISOString()
            })
        };

        const command = new SendMessageCommand(params);
        await sqs.send(command);

        console.log(`[Producer] Mensaje encolado exitosamente: ${data.id_liquidacion}`);

        return {
            statusCode: 202,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: "Liquidación recibida y encolada correctamente", id_liquidacion: data.id_liquidacion })
        };

    } catch (error) {
        console.error("[Producer Error]", error);
        return {
            statusCode: 500,
            body: JSON.stringify({ error: "Error interno al procesar la solicitud" })
        };
    }
};