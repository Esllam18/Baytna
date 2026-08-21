import React from "react";
import { Redirect } from "expo-router";
import { ActivityIndicator, SafeAreaView, StyleSheet } from "react-native";
import { useAuth } from "../src/auth/AuthProvider";
import { colors } from "../src/theme/tokens";
export default function Index(){const {status}=useAuth(); if(status==="loading") return <SafeAreaView style={s.wrap}><ActivityIndicator color={colors.orange}/></SafeAreaView>; return <Redirect href={status==="authenticated"?"/home":"/auth/phone"}/>}
const s=StyleSheet.create({wrap:{flex:1,alignItems:"center",justifyContent:"center",backgroundColor:colors.canvas}});
