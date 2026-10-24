import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import DeviceTest from "@/pages/DeviceTest";
import Clients from "@/pages/Clients";
import ClientDetail from "@/pages/ClientDetail";
import RoutesPage from "@/pages/Routes";
import RouteBuilder from "@/pages/RouteBuilder";
import AssignExercise from "@/pages/AssignExercise";
import RunPage from "@/pages/RunPage";

function Workspace() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/device-test" element={<DeviceTest />} />
        <Route path="/clients" element={<Clients />} />
        <Route path="/clients/:id" element={<ClientDetail />} />
        <Route path="/routes" element={<RoutesPage />} />
        <Route path="/routes/:id" element={<RouteBuilder />} />
        <Route path="/routes/:id/assign" element={<AssignExercise />} />
      </Routes>
    </Layout>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/run/:id" element={<Layout nav={false}><RunPage /></Layout>} />
        <Route path="*" element={<Workspace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
