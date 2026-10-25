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
import ScanRoute from "@/pages/ScanRoute";
import LiveScreen from "@/pages/LiveScreen";
import AttemptReview from "@/pages/AttemptReview";
import NotePrint from "@/pages/NotePrint";
import ReplayScreen from "@/pages/ReplayScreen";
import Landing from "@/pages/Landing";
import Research from "@/pages/Research";
import DemoRouteSetting from "@/components/replay/DemoRouteSetting";
import { useParams } from "react-router-dom";

function ReplayWatch() {
  const { id } = useParams();
  return <ReplayScreen isPublic attemptId={id} />;
}

function RouteReplay() {
  const { id } = useParams();
  return (
    <>
      <ReplayScreen routeId={id} />
      <DemoRouteSetting routeId={id} />
    </>
  );
}

function Workspace() {
  return (
    <Layout>
      <Routes>
        <Route path="/workspace" element={<Home />} />
        <Route path="/device-test" element={<DeviceTest />} />
        <Route path="/clients" element={<Clients />} />
        <Route path="/clients/:id" element={<ClientDetail />} />
        <Route path="/routes" element={<RoutesPage />} />
        <Route path="/routes/:id" element={<RouteBuilder />} />
        <Route path="/routes/:id/assign" element={<AssignExercise />} />
        <Route path="/teach/:id" element={<TeachWalk />} />
        <Route path="/teach/:id/review" element={<TeachReview />} />
        <Route path="/scan/:id" element={<ScanRoute />} />
        <Route path="/live/:id" element={<LiveScreen />} />
        <Route path="/review/:id" element={<AttemptReview />} />
        <Route path="/routes/:id/replay" element={<RouteReplay />} />
      </Routes>
    </Layout>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/run/:id" element={<Layout nav={false}><ClientRun /></Layout>} />
        <Route path="/demo" element={<Layout nav={false} home="/"><ReplayScreen isPublic /></Layout>} />
        <Route path="/replay/:id" element={<Layout nav={false} home="/"><ReplayWatch /></Layout>} />
        <Route path="/" element={<Layout nav={false} home="/"><Landing /></Layout>} />
        <Route path="/research" element={<Layout nav={false} home="/"><Research /></Layout>} />
        <Route path="/notes/:id/print" element={<NotePrint />} />
        <Route path="*" element={<Workspace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
