import React from "react";
import { Line } from "react-chartjs-2";
import Draggable from "react-draggable";
import "../assets/styles/ChartCard.css";

function ChartCard({ title, data, onClose }) {
  // Encapsulamos todo el contenido en un único <div>
  const content = (
    <div className="chart-card-floating">
      <button className="chart-card-close" onClick={onClose}>
        ✕
      </button>
      <h3 className="chart-card-title">{title}</h3>
      <Line data={data} />
    </div>
  );

  // Ahora envolvemos 'content' en otro <div> para asegurar un único nodo hijo
  return (
    <Draggable handle=".chart-card-title" bounds="parent">
      <div>{content}</div>
    </Draggable>
  );
}

export default ChartCard;
