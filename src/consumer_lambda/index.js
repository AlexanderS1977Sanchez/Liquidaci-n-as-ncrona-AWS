const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, PutCommand } = require("@aws-sdk/lib-dynamodb");

const client = new DynamoDBClient({});
const dynamo = DynamoDBDocumentClient.from(client);

exports.handler = async (event) => {
    for (const record of event.Records) {
        try {
            const body = JSON.parse(record.body);
            const { id_liquidacion, cantidad_kg, precio_kg, descuentos } = body;

            // Cálculo del valor liquidado
            const valor_liquidado = (Number(cantidad_kg) * Number(precio_kg)) - Number(descuentos);

            const itemToSave = {
                ...body,
                valor_liquidado: valor_liquidado,
                estado: "liquidado",
                fecha_procesamiento: new Date().toISOString()
            };

            // Idempotencia: Escritura condicional en DynamoDB si la clave primaria ya existe no sobreescribe de forma duplicada o errónea
            const params = {
                TableName: process.env.DYNAMODB_TABLE,
                Item: itemToSave,
                ConditionExpression: "attribute_not_exists(id_liquidacion)"
            };

            try {
                await dynamo.send(new PutCommand(params));
                console.log(`[Consumer] Liquidación procesada y guardada con éxito: ${id_liquidacion}`);
            } catch (err) {
                if (err.name === "ConditionalCheckFailedException") {
                    console.warn(`[Consumer] Advertencia: Intento duplicado detectado para id_liquidacion: ${id_liquidacion}. Omitiendo pago duplicado.`);
                } else {
                    throw err;
                }
            }

        } catch (error) {
            console.error("[Consumer Error processing record]", error);
            // Lanzar el error permite que SQS reintente y mueva el mensaje a la DLQ tras agotar los reintentos
            throw error; 
        }
    }
};