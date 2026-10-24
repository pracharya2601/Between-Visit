import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import DeviceTest from "@/pages/DeviceTest";
import Clients from "@/pages/Clients";
import ClientDetail from "@/pages/ClientDetail";
import RoutesPage from "@/pages/Routes";
import RouteBuilder from "@/pages/RouteBuilder";

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/device-test" element={<DeviceTest />} />
          <Route path="/clients" element={<Clients />} />
          <Route path="/clients/:id" element={<ClientDetail />} />
          <Route path="/routes" element={<RoutesPage />} />
          <Route path="/routes/:id" element={<RouteBuilder />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
