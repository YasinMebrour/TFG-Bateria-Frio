// src/pages/ConfiguracionPage.jsx
import React from 'react';
import styles from '../../assets/styles/Config.module.css';

import TarifaConfigPage from './TarifaConfigPage';
import UsuariosConfigPage from './UsuariosConfigPage';
import PrediccionesConfigPage from './PrediccionesConfigPage';
import EventRulesPage from './EventRulesPage';

export default function ConfiguracionPage() {
  return (
    <div className={styles.demo}>
      <div className={styles.tab}>
        <div className={styles['tab-wrapper']}>
          {/* ---------- Tab 1 ---------- */}
          <input id="tab1" type="radio" name="tabsA" defaultChecked />
          <label htmlFor="tab1">Tarifas</label>
          <div className={styles['tab-content']}>
            <TarifaConfigPage />
          </div>

          {/* ---------- Tab 2 ---------- */}
          <input id="tab2" type="radio" name="tabsA" />
          <label htmlFor="tab2">Usuarios</label>
          <div className={styles['tab-content']}>
            <UsuariosConfigPage />
          </div>


          {/* ---------- Tab 4 ---------- */}
          <input id="tab3" type="radio" name="tabsA" />
          <label htmlFor="tab3">Bandas</label>
          <div className={styles['tab-content']}>
            <PrediccionesConfigPage />
          </div>

          {/* ---------- Tab 4 ---------- */}
          <input id="tab4" type="radio" name="tabsA" />
          <label htmlFor="tab4">Eventos</label>
          <div className={styles['tab-content']}>
            <EventRulesPage />
          </div>

        </div>
      </div>
    </div>
  );
}
