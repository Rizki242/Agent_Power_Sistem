import React from 'react';
import { BrowserRouter, useRoutes } from 'react-router-dom';
import { UIStoreProvider } from '../stores/uiStore';
import { TreeStoreProvider } from '../stores/treeStore';
import { routes } from './routes';

function AppRoutes() {
  return useRoutes(routes);
}

// Application root: providers (theme, asset tree) + router. The actual
// shell (sidebar/topbar/breadcrumb) lives in layouts/WorkspaceLayout.jsx,
// wired in as the routes' shared parent element.
export default function App() {
  return (
    <BrowserRouter>
      <UIStoreProvider>
        <TreeStoreProvider>
          <AppRoutes />
        </TreeStoreProvider>
      </UIStoreProvider>
    </BrowserRouter>
  );
}
