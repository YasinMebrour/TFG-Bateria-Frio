import React from 'react';
import SingleDaySlider from '../../components/SingleDaySlider';

const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

export default function ModoAhorroDiaEditor({
  intervalsByDay,
  setIntervalsByDay,
  editingDay,
  setEditingDay,
  isEditor
}) {

  const handleSliderChange = (newIntervals) => {
    setIntervalsByDay(prev => ({ ...prev, [editingDay]: newIntervals }));
  };

/* Gemelo o ModoAhorroDiaEditor.jsx */

return (
  <div className="dia-editor">

    {/* ───── Caja agrupadora ───── */}
    <div
      className="modo-ahorro-box"
      style={{
        border:       '1px solid #ccc',
        borderRadius: 6,
        padding:      '1rem',
        background:   '#fafafa'
      }}
    >
      {/* Fila de botones */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          marginBottom: '3rem'     /* separación con el slider */
        }}
      >
        <div style={{ width: 140, fontWeight: 600, textAlign: 'right', marginRight: '.75rem' }}>
          Días con modo ahorro
        </div>

        <div style={{ flex: 1, display: 'flex', gap: '.5rem' }}>
          {days.map(day => {
            const hasData  = intervalsByDay[day]?.length > 0;
            const isActive = editingDay === day;
            const bg  = hasData ? '#007bff' : '#fff';
            const brd = isActive ? '3px solid rgb(0, 0, 0)' : '1px solid #ccc';
            return (
              <button
                key={day}
                disabled={!isEditor}
                onClick={() => isEditor && setEditingDay(day)}
                title={!isEditor ? 'Acceso solo para editores' : ''}
                style={{
                  flex: 1,
                  padding: '.5rem 0',
                  background: bg,
                  border: brd,
                  borderRadius: 4,
                  cursor: isEditor ? 'pointer' : 'not-allowed',
                  color: '#000'
                }}
              >
                {day}
              </button>
            );
          })}
        </div>
      </div>

      {/* Fila del slider */}
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{ width: 140, fontWeight: 600, textAlign: 'right', marginRight: '.75rem' }}>
          Horas modo ahorro
        </div>

        <div style={{ flex: 1 }}>
          <SingleDaySlider
            key={editingDay}
            intervals={intervalsByDay[editingDay] || []}
            onChange={arr =>
              setIntervalsByDay(prev => ({ ...prev, [editingDay]: arr }))
            }
            disabled={!isEditor}
          />
        </div>
      </div>
    </div> {/* fin caja */}
  </div>
);

}
