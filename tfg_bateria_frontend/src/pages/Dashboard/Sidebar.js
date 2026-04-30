// src/components/Sidebar.js
import React, { useState, useMemo } from "react";
import { useBuckets }                       from "../../hooks/useBuckets";
import { useMeasurementsByBucket }          from "../../hooks/useMeasurementsByBucket";
import { useFieldsByBucketMeasurement }     from "../../hooks/useFieldsByBucketMeasurement";
import "../../assets/styles/Sidebar.css";
import { useAuth } from '../../context/AuthContext';


/* -------------------------------------------------------------
 * Convierte cualquier valor del backend a string seguro para
 * mostrar o usar como key. 
 * ----------------------------------------------------------- */
import ReactIs from "react-is";
const toName = (value) => {
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (value == null) return "";
  if (ReactIs.isElement(value)) {
    console.warn("[Sidebar] React Element recibido:", value);
    return value.type?.displayName || value.type?.name || "<ReactElement>";
  }
  return (
    value.name ??
    value.bucket ??
    value.id ??
    value.measurement ??
    JSON.stringify(value)
  );
};

function Sidebar() {
  const { authFetch } = useAuth();
  const [openBuckets, setOpenBuckets]           = useState(new Set());
  const [openMeasurements, setOpenMeasurements] = useState(new Set());

  const { data: rawBuckets = [], isLoading } = useBuckets(authFetch);
  const buckets = useMemo(() => rawBuckets.map(toName), [rawBuckets]);

  const measurementsByBucket = useMeasurementsByBucket(buckets, openBuckets, authFetch);

  const fieldsByBucketMeasurement = useFieldsByBucketMeasurement(openMeasurements, authFetch);

  const toggleBucket = (bucket) => {
    setOpenBuckets((prev) => {
      const next = new Set(prev);
      next.has(bucket) ? next.delete(bucket) : next.add(bucket);
      return next;
    });
  };
  const toggleMeasurement = (bucket, measurement) => {
    const composite = `${bucket}|${measurement}`;
    setOpenMeasurements((prev) => {
      const next = new Set(prev);
      next.has(composite) ? next.delete(composite) : next.add(composite);
      return next;
    });
  };

  return (
    <div className="sidebar">
      <h2 className="title">INIT</h2>
      <div className="list">
        {buckets.map((bucket) => (
          <div key={bucket} className="bucket-container">
            <div className="bucket-header" onClick={() => toggleBucket(bucket)}>
              <span className="text">{bucket}</span>
              <span className="icon">
                {openBuckets.has(bucket) ? "−" : "+"}
              </span>
            </div>

            {/* Measurements */}
            {openBuckets.has(bucket) && (
              <div className="measurements-container">
                {measurementsByBucket[bucket].map((measurement) => {
                  const composite = `${bucket}|${measurement}`;
                  return (
                    <div key={composite} className="measurement-container">
                      <div
                        className="measurement-header"
                        onClick={() => toggleMeasurement(bucket, measurement)}
                      >
                        <span className="text">{measurement}</span>
                        <span className="icon">
                          {openMeasurements.has(composite) ? "−" : "+"}
                        </span>
                      </div>

                      {/* Fields */}
                      {openMeasurements.has(composite) && (
                        <div className="fields-container">
                          {fieldsByBucketMeasurement[composite].map((field) => (
                            <div
                              key={field}
                              className="field-item"
                              draggable
                              onDragStart={(e) =>
                                e.dataTransfer.setData(
                                  "application/json",
                                  JSON.stringify({ bucket, measurement, field })
                                )
                              }
                            >
                              {field}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default Sidebar;
