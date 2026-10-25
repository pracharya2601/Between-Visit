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
import ClientRun from "@/pages/ClientRun";
import TeachWalk from "@/pages/TeachWalk";
import TeachReview from "@/pages/TeachReview";
import AttemptReview from "@/pages/AttemptReview";
import NotePrint from "@/pages/NotePrint";

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
        <Route path="/teach/:id" element={<TeachWalk />} />
        <Route path="/teach/:id/review" element={<TeachReview />} />
        <Route path="/review/:id" element={<AttemptReview />} />
      </Routes>
    </Layout>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/run/:id" element={<Layout nav={false}><ClientRun /></Layout>} />
        <Route path="/notes/:id/print" element={<NotePrint />} />
        <Route path="*" element={<Workspace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
