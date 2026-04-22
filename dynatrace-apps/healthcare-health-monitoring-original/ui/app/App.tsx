import { Page } from "@dynatrace/strato-components-preview/layouts";
import React, { useState, useCallback } from "react";
import { Route, Routes } from "react-router-dom";
import { DqlQueryParamsProvider } from "@dynatrace-sdk/react-hooks";
import type { Timeframe, TimeValue } from "@dynatrace/strato-components/core";
import { Header } from "./components/Header";
import { Overview } from "./pages/Overview";
import { EpicHealth } from "./pages/EpicHealth";
import { NetworkHealth } from "./pages/NetworkHealth";
import { IntegrationHealth } from "./pages/IntegrationHealth";
import { SiteView } from "./pages/SiteView";
import { Explore } from "./pages/Explore";
import { SecurityCompliance } from "./pages/SecurityCompliance";
import { MyChartPortal } from "./pages/MyChartPortal";

function createInitialTimeframe(): Timeframe {
  const now = new Date();
  const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000);
  return {
    from: { value: "now()-2h", type: "expression", absoluteDate: twoHoursAgo.toISOString() },
    to: { value: "now()", type: "expression", absoluteDate: now.toISOString() },
  };
}

const toGrailTimeframe = (tv: TimeValue): string =>
  (tv.absoluteDate && tv.absoluteDate.length > 0) ? tv.absoluteDate : tv.value;

export const App = () => {
  const [timeframe, setTimeframe] = useState<Timeframe>(createInitialTimeframe);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = useCallback(() => {
    // Re-create the timeframe to force DqlQueryParamsProvider to re-execute all queries
    const now = new Date();
    setTimeframe((prev) => ({
      from: prev.from,
      to: { ...prev.to, absoluteDate: now.toISOString() },
    }));
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <Page>
      <Page.Header>
        <Header timeframe={timeframe} onTimeframeChange={(tf) => { if (tf) setTimeframe(tf); }} onRefresh={handleRefresh} />
      </Page.Header>
      <Page.Main>
        <DqlQueryParamsProvider
          key={refreshKey}
          defaultTimeframeStart={toGrailTimeframe(timeframe.from)}
          defaultTimeframeEnd={toGrailTimeframe(timeframe.to)}
        >
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/epic" element={<EpicHealth />} />
            <Route path="/network" element={<NetworkHealth />} />
            <Route path="/integration" element={<IntegrationHealth />} />
            <Route path="/sites" element={<SiteView />} />
            <Route path="/security" element={<SecurityCompliance />} />
            <Route path="/mychart" element={<MyChartPortal />} />
            <Route path="/explore" element={<Explore />} />
          </Routes>
        </DqlQueryParamsProvider>
      </Page.Main>
    </Page>
  );
};
