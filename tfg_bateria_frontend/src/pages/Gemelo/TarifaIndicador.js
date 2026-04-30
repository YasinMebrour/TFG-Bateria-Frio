// TarifaIndicator.js
import React, { useEffect, useState } from 'react';
import { useApi } from '../../hooks/useApi';

const colores = { P1:'#ff0000', P2:'#ffeb00', P3:'#0070bf',
                  P4:'#ff00ff', P5:'#ff9900', P6:'#00af50' };

                 
export default function TarifaIndicator({ date }) {

    const [tarifas, setTarifas] = useState([]);

    const api = useApi();
    

    useEffect(() => {
        if (!date) return;
        api.get(`/tarifas/dia?start_date=${date}`)
        .then(j => setTarifas(j.tarifas))
        .catch(console.error);
    }, [date]);

    if (tarifas.length === 0) return null;

    // Agrupar horas idénticas en segmentos
    const segmentos = [];
    let curr = { tarifa: tarifas[0], start: 0 };
    for (let h = 1; h <= tarifas.length; h++) {
        if (h === tarifas.length || tarifas[h] !== curr.tarifa) {
        segmentos.push({ ...curr, end: h });
        if (h < tarifas.length) curr = { tarifa: tarifas[h], start: h };
        }
    }

    return (
        <div style={{
        display: 'flex',
        margin: '8px 0',
        height: '24px',          // más alto para que quepa el texto
        fontSize: '12px',
        fontFamily: 'sans-serif'
        }}>
        {segmentos.map((s, i) => (
            <div
            key={i}
            title={`${s.start}:00 – ${s.end}:00   ${s.tarifa}`}
            style={{
                flex: s.end - s.start,
                background: colores[s.tarifa] || '#ccc',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontWeight: 'bold', // <-- así se escribe en React
                whiteSpace: 'nowrap',
                overflow: 'hidden'
            }}

            >
            {`${s.start}:00–${s.end}:00 ${s.tarifa}`}
            </div>
        ))}
        </div>
    );
    }
