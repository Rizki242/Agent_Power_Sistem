import React, { useState, useEffect } from 'react';
import { WorkOrderSummaryCards, WorkOrderTable, WorkOrderDetailCard } from '../components/workorder';
import { apiUrl } from '../api';

export default function WorkOrderCenter() {
  const [workOrders, setWorkOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedWO, setSelectedWO] = useState(null);
  const [engineerName, setEngineerName] = useState('Chief Reliability Engineer');

  const fetchWorkOrders = () => {
    setLoading(true);
    fetch(apiUrl('/api/workorders'))
      .then(res => res.json())
      .then(data => {
        setWorkOrders(data.work_orders || []);
        setLoading(false);
        if (data.work_orders && data.work_orders.length > 0 && !selectedWO) {
          setSelectedWO(data.work_orders[0]);
        }
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchWorkOrders();
  }, []);

  const handleAction = async (action) => {
    if (!selectedWO) return;
    try {
      const res = await fetch(apiUrl('/api/workorders/approve'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wo_number: selectedWO.wo_number,
          approved_by: engineerName,
          action: action
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setSelectedWO(data.work_order);
        fetchWorkOrders();
      }
    } catch (err) {
      console.error(err);
      alert('Gagal memproses otorisasi Work Order.');
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-cyan font-black">Maintenance Decision &amp; EAM</div>
          <h2 className="text-xl font-bold text-textMain mt-0.5">Work Order &amp; Human-in-the-Loop Center</h2>
        </div>
        <div className="flex items-center gap-2">
          <input 
            type="text" 
            value={engineerName}
            onChange={(e) => setEngineerName(e.target.value)}
            title="Nama Otorisator"
            className="bg-panel2 border border-line rounded-lg px-3 py-1 text-xs text-textMain outline-none focus:border-cyan text-right"
          />
        </div>
      </div>

      {/* Summary Cards */}
      <WorkOrderSummaryCards workOrders={workOrders} />

      {/* Main Grid Layout */}
      <section className="grid lg:grid-cols-[1.4fr_1.1fr] gap-4">
        {/* Left: Work Order List */}
        <WorkOrderTable
          workOrders={workOrders}
          loading={loading}
          selectedWO={selectedWO}
          onSelectWO={setSelectedWO}
          onAction={handleAction}
        />

        {/* Right: Selected Work Order Detail & HITL Approval */}
        <WorkOrderDetailCard
          selectedWO={selectedWO}
          engineerName={engineerName}
          onAction={handleAction}
        />
      </section>
    </div>
  );
}
