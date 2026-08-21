export const driverKeys={
  profile:["driver","profile"] as const,
  dashboard:["driver","dashboard"] as const,
  availableMissions:["driver","missions","available"] as const,
  availableMission:(id:string)=>["driver","missions","available",id] as const,
  currentMission:["driver","missions","current"] as const,
  mission:(id:string)=>["driver","mission",id] as const,
  history:["driver","missions","history"] as const,
};
