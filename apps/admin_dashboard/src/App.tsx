import React from "react";
import {BrowserRouter,Navigate,Route,Routes} from "react-router-dom";
import {useAuth} from "./auth/AuthProvider";
import {AppShell} from "./components/AppShell";
import {Loading} from "./components/Ui";
import {LoginPage} from "./pages/Login";
import {DashboardPage} from "./pages/Dashboard";
import {ControlRoomPage} from "./pages/ControlRoom";
import {PilotPage} from "./pages/Pilot";
import {EconomicsPage} from "./pages/Economics";
import {FinancialAutomationPage} from "./pages/FinancialAutomation";
import {TrafficGovernancePage} from "./pages/TrafficGovernance";
import {VendorAccountingPage} from "./pages/VendorAccounting";
import {LaunchCommandPage} from "./pages/LaunchCommand";
import {PostLaunchPage} from "./pages/PostLaunch";
import {OrdersPage} from "./pages/Orders";
import {OrderDetailPage} from "./pages/OrderDetail";
import {ChefsPage} from "./pages/Chefs";
import {ChefDetailPage} from "./pages/ChefDetail";
import {DriversPage} from "./pages/Drivers";
import {DriverDetailPage} from "./pages/DriverDetail";
import {SupportPage} from "./pages/Support";
import {TicketDetailPage} from "./pages/TicketDetail";
import {FinancePage} from "./pages/Finance";
import {AuditPage} from "./pages/Audit";
import {DiagnosticsPage} from "./pages/Diagnostics";

function Protected(){
  const auth=useAuth();
  if(!auth.ready)return <div className="boot"><Loading label="بنفتح لوحة الإدارة..."/></div>;
  return auth.authenticated?<AppShell/>:<Navigate to="/login" replace/>;
}

export function App(){
  return <BrowserRouter>
    <Routes>
      <Route path="/login" element={<LoginPage/>}/>
      <Route element={<Protected/>}>
        <Route path="/" element={<DashboardPage/>}/>
        <Route path="/control-room" element={<ControlRoomPage/>}/>
        <Route path="/pilot" element={<PilotPage/>}/>
        <Route path="/economics" element={<EconomicsPage/>}/>
        <Route path="/finance-automation" element={<FinancialAutomationPage/>}/>
        <Route path="/traffic-governance" element={<TrafficGovernancePage/>}/>
        <Route path="/vendor-accounting" element={<VendorAccountingPage/>}/>
        <Route path="/launch-command" element={<LaunchCommandPage/>}/>
        <Route path="/post-launch" element={<PostLaunchPage/>}/>
        <Route path="/orders" element={<OrdersPage/>}/>
        <Route path="/orders/:orderId" element={<OrderDetailPage/>}/>
        <Route path="/chefs" element={<ChefsPage/>}/>
        <Route path="/chefs/:chefId" element={<ChefDetailPage/>}/>
        <Route path="/drivers" element={<DriversPage/>}/>
        <Route path="/drivers/:driverId" element={<DriverDetailPage/>}/>
        <Route path="/support" element={<SupportPage/>}/>
        <Route path="/support/:ticketId" element={<TicketDetailPage/>}/>
        <Route path="/finance" element={<FinancePage/>}/>
        <Route path="/audit" element={<AuditPage/>}/>
        <Route path="/diagnostics" element={<DiagnosticsPage/>}/>
      </Route>
      <Route path="*" element={<Navigate to="/" replace/>}/>
    </Routes>
  </BrowserRouter>;
}
