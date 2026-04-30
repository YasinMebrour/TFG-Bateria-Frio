import React, { useState, useEffect } from 'react';
import Plot from 'plotly.js-basic-dist';
import createPlotlyComponent from 'react-plotly.js/factory';
import "../../assets/styles/Charts.css";

const Plotly = createPlotlyComponent(Plot);

// Convierte tu array [{ hora, consumo }] en [{ x: Date, y: number }]
const process = (ds = []) =>
  ds
    .map(i => ({
      x: new Date(i.hora),
      y: Number(i.humedad)
    }))
    .filter(d => !isNaN(d.x) && !isNaN(d.y));

const DATE_FMT = { hour:'2-digit', minute:'2-digit', day:'numeric', month:'short' };

export default function HumedadManualChart({ humedadManual = [] }) {
  const [series, setSeries] = useState([]);
  const [range,  setRange]  = useState([null, null]);
  const [loading, setLoading] = useState(true);

  // Cuando cambian los datos de humedadManual, reprocesamos y centramos el rango
  useEffect(() => {
    setLoading(true);

    if (humedadManual.length === 0) {
      // no hay nada que procesar
      setLoading(false);
      return;
    }
    if (humedadManual.length === 0) return;
    const pts = process(humedadManual);
    setSeries(pts);

    setLoading(false);
  }, [humedadManual]);

  // Handler de zoom/pan
  const onRelayout = ({ 'xaxis.range[0]': s, 'xaxis.range[1]': e }) => {
    if (s && e) {
      setRange([ new Date(s), new Date(e) ]);
    }
  };

  if (loading) {
    return (
      <div className="spinner-container">
        <div className="spinner"/>
      </div>
    );
  }

  return (
    <div className="charts-container">
      <Plotly
        data={[{
          x: series.map(p => p.x),
          y: series.map(p => p.y),
          type: 'scatter',
          mode: 'lines',
          line: { color: '#0070bf' },
          hovertemplate: `<b>%{x|${DATE_FMT}}</b><br>Consumo: %{y:.2f} kWh<extra></extra>`
        }]}
        layout={{
          xaxis: {
            type: 'date',
            range: range,
            rangeslider:{ visible:true },
            rangeselector:{ buttons:[
              {count:1,label:'1h', step:'hour',stepmode:'backward'},
              {count:6,label:'6h', step:'hour',stepmode:'backward'},
              {count:12,label:'12h',step:'hour',stepmode:'backward'},
              {count:1,label:'1d', step:'day', stepmode:'backward'},
              {step:'all'}
            ]}
          },
          yaxis: {
            title: { text: 'kWh', standoff:20 }
          },
          title: { text: 'Consumo Manual', font:{ size:18 } },
          template: 'plotly_white',
          hovermode: 'x unified',
          margin: { t:40,b:40,l:60,r:30 },
          height: 400
        }}
        onRelayout={onRelayout}
        useResizeHandler
        style={{ width:'100%', minHeight:'400px' }}
      />
    </div>
  );
}
