import React from 'react';
import { Navigate } from 'react-router-dom';
import WorkspaceLayout from '../layouts/WorkspaceLayout';
import Dashboard from '../pages/Dashboard';
import ReliabilityCommandCenter from '../pages/ReliabilityCommandCenter';
import AssetHealth from '../pages/AssetHealth';
import DigitalTwinWorkspace from '../pages/DigitalTwinWorkspace';
import KnowledgeWorkspace from '../pages/KnowledgeWorkspace';
import WorkOrderCenter from '../pages/WorkOrderCenter';
import EngineeringModules from '../pages/EngineeringModules';
import MCSAWorkspace from '../modules/mcsa/MCSAWorkspace';
import VibWorkspace from '../modules/vibration/VibWorkspace';
import DGAWorkspace from '../modules/dga/DGAWorkspace';
import TribologyWorkspace from '../modules/tribology/TribologyWorkspace';
import ThermalWorkspace from '../modules/thermal/ThermalWorkspace';
import PDWorkspace from '../modules/partial_discharge/PDWorkspace';

// One entry per engineering module id from /api/v2/modules. Each workspace
// reads the selected equipment from its own :equipmentId route param
// (docs/final.md Phase 25 / desaindakhir.md redesign) - this route table is
// the only place that needs a new line for a future module getting its own
// workspace page (plus a DOMAIN_EQUIPMENT_SOURCES entry in
// services/assetTree.js so its equipment appears under the sidebar tree).
//
// Legacy top-level paths (/mcsa, /vibration, ...) redirect into
// /workspace/<module> so existing bookmarks/links keep working.
export const routes = [
  {
    element: <WorkspaceLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'fusion', element: <ReliabilityCommandCenter /> },
      { path: 'twin', element: <DigitalTwinWorkspace /> },
      { path: 'health', element: <AssetHealth /> },
      { path: 'workorders', element: <WorkOrderCenter /> },
      { path: 'knowledge', element: <KnowledgeWorkspace /> },
      { path: 'engineering-modules', element: <EngineeringModules /> },

      { path: 'workspace/mcsa/:equipmentId?', element: <MCSAWorkspace /> },
      { path: 'workspace/vibration/:equipmentId?', element: <VibWorkspace /> },
      { path: 'workspace/dga/:equipmentId?', element: <DGAWorkspace /> },
      { path: 'workspace/tribology/:equipmentId?', element: <TribologyWorkspace /> },
      { path: 'workspace/thermal/:equipmentId?', element: <ThermalWorkspace /> },
      { path: 'workspace/partial_discharge/:equipmentId?', element: <PDWorkspace /> },

      { path: 'mcsa', element: <Navigate to="/workspace/mcsa" replace /> },
      { path: 'vibration', element: <Navigate to="/workspace/vibration" replace /> },
      { path: 'dga', element: <Navigate to="/workspace/dga" replace /> },
      { path: 'tribology', element: <Navigate to="/workspace/tribology" replace /> },
      { path: 'thermal', element: <Navigate to="/workspace/thermal" replace /> },
      { path: 'pd', element: <Navigate to="/workspace/partial_discharge" replace /> },

      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
];
