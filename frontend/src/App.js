import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import DeviceTest from "@/pages/DeviceTest";

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/device-test" element={<DeviceTest />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
