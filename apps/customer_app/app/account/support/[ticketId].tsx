import React, { useState } from "react";
import { Image, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import * as ImagePicker from "expo-image-picker";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Screen } from "../../../src/ui/Screen";
import { PrimaryButton } from "../../../src/ui/PrimaryButton";
import { ErrorState, LoadingState } from "../../../src/ui/StateViews";
import { useSupportTicket } from "../../../src/hooks/useAccount";
import { customerApi } from "../../../src/api";
import { queryKeys } from "../../../src/query/keys";
import { uploadSupportAttachment, LocalAttachment } from "../../../src/media/uploadSupportAttachment";
import { colors, radius } from "../../../src/theme/tokens";

export default function SupportTicketScreen() {
  const { ticketId } = useLocalSearchParams<{ ticketId: string }>();
  const id = String(ticketId ?? "");
  const q = useSupportTicket(id);
  const [message, setMessage] = useState("");
  const [attachment, setAttachment] = useState<LocalAttachment | null>(null);
  const [attachmentError, setAttachmentError] = useState("");
  const qc = useQueryClient();

  const chooseImage = async () => {
    setAttachmentError("");
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setAttachmentError("اسمح بالوصول للصور لإضافة المرفق.");
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 0.8,
      allowsEditing: false,
    });
    if (result.canceled) return;
    const asset = result.assets[0];
    const mimeType = normalizeMime(asset.mimeType, asset.fileName);
    if (!mimeType) {
      setAttachmentError("الصيغة غير مدعومة.");
      return;
    }
    setAttachment({
      uri: asset.uri,
      fileName: asset.fileName ?? "support-reply.jpg",
      mimeType,
      fileSize: asset.fileSize,
    });
  };

  const send = useMutation({
    mutationFn: async () => {
      const ids: string[] = [];
      if (attachment) {
        ids.push((await uploadSupportAttachment(attachment)).id);
      }
      return customerApi.addSupportMessage(id, message.trim(), ids);
    },
    onSuccess: async () => {
      setMessage("");
      setAttachment(null);
      await Promise.all([
        qc.invalidateQueries({ queryKey: queryKeys.supportTicket(id) }),
        qc.invalidateQueries({ queryKey: queryKeys.supportTickets }),
      ]);
    },
  });

  if (q.isLoading) return <Screen><LoadingState label="بنفتح المحادثة..." /></Screen>;
  if (q.isError || !q.data) return <Screen><ErrorState message="تعذر فتح طلب الدعم." /></Screen>;
  const ticket = q.data;
  const closed = ["resolved", "closed"].includes(ticket.status);

  return (
    <Screen>
      <View style={s.header}>
        <Text onPress={() => router.back()} style={s.back}>→</Text>
        <View style={{ flex: 1 }}>
          <Text style={s.title}>{ticket.subject}</Text>
          <Text style={s.status}>{ticket.status}</Text>
        </View>
      </View>

      <View style={s.original}>
        <Text style={s.originalLabel}>وصف المشكلة</Text>
        <Text style={s.originalText}>{ticket.description}</Text>
      </View>

      <Text style={s.section}>المحادثة</Text>
      {ticket.messages.map((msg) => (
        <View
          key={msg.id}
          style={[s.message, msg.sender_role === "customer" ? s.mine : s.theirs]}
        >
          <Text style={s.sender}>{msg.sender_role === "customer" ? "أنت" : "فريق بيتنا"}</Text>
          <Text style={s.messageText}>{msg.body}</Text>
          {msg.attachments?.length ? (
            <Text style={s.attachmentsText}>{msg.attachments.length} مرفق</Text>
          ) : null}
          <Text style={s.time}>{new Date(msg.created_at).toLocaleString("ar-EG")}</Text>
        </View>
      ))}

      {closed ? (
        <View style={s.closed}>
          <Text style={s.closedTitle}>تم إغلاق هذه التذكرة</Text>
          {ticket.resolution_note ? <Text style={s.closedText}>{ticket.resolution_note}</Text> : null}
        </View>
      ) : (
        <View style={s.reply}>
          <TextInput
            value={message}
            onChangeText={setMessage}
            placeholder="اكتب ردك..."
            placeholderTextColor="#A2968C"
            multiline
            style={s.input}
            textAlign="right"
          />
          {attachment ? (
            <Pressable onPress={() => setAttachment(null)} style={s.replyPreviewWrap}>
              <Image source={{ uri: attachment.uri }} style={s.replyPreview} />
              <Text style={s.removeLabel}>إزالة الصورة</Text>
            </Pressable>
          ) : (
            <Pressable onPress={() => void chooseImage()}>
              <Text style={s.addAttachment}>＋ أضف صورة</Text>
            </Pressable>
          )}
          {attachmentError ? <Text style={s.error}>{attachmentError}</Text> : null}
          <PrimaryButton
            label="إرسال الرد"
            onPress={() => send.mutate()}
            loading={send.isPending}
            disabled={!message.trim()}
          />
          {send.isError ? <Text style={s.error}>تعذر رفع المرفق أو إرسال الرد.</Text> : null}
        </View>
      )}
    </Screen>
  );
}

function normalizeMime(
  mime?: string | null,
  fileName?: string | null,
): LocalAttachment["mimeType"] | null {
  if (mime === "image/jpeg" || mime === "image/png" || mime === "image/webp") return mime;
  const lower = (fileName ?? "").toLowerCase();
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "image/jpeg";
  if (lower.endsWith(".png")) return "image/png";
  if (lower.endsWith(".webp")) return "image/webp";
  return null;
}

const s = StyleSheet.create({
  header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:14,paddingBottom:14},
  back:{fontSize:26},
  title:{fontSize:19,fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  status:{fontSize:10,color:colors.orangeDark,textAlign:"right",marginTop:3},
  original:{backgroundColor:colors.soft,borderRadius:radius.md,padding:14},
  originalLabel:{fontSize:10,fontWeight:"900",color:colors.muted,textAlign:"right"},
  originalText:{color:colors.ink,textAlign:"right",writingDirection:"rtl",lineHeight:20,marginTop:5},
  section:{fontSize:16,fontWeight:"900",color:colors.ink,textAlign:"right",marginTop:20,marginBottom:9},
  message:{maxWidth:"88%",borderRadius:16,padding:12,marginBottom:10},
  mine:{alignSelf:"flex-start",backgroundColor:colors.orangeSoft},
  theirs:{alignSelf:"flex-end",backgroundColor:colors.surface,borderWidth:1,borderColor:colors.border},
  sender:{fontSize:9,fontWeight:"900",color:colors.muted,textAlign:"right"},
  messageText:{color:colors.ink,textAlign:"right",writingDirection:"rtl",lineHeight:19,marginTop:3},
  attachmentsText:{fontSize:9,color:colors.orangeDark,fontWeight:"900",textAlign:"right",marginTop:5},
  time:{fontSize:8,color:"#9B8F85",marginTop:5,textAlign:"right"},
  reply:{gap:10,marginTop:12},
  input:{minHeight:90,borderWidth:1,borderColor:colors.border,borderRadius:radius.md,backgroundColor:colors.surface,padding:12,textAlignVertical:"top",writingDirection:"rtl"},
  replyPreviewWrap:{alignItems:"flex-end"},
  replyPreview:{width:100,height:100,borderRadius:14},
  removeLabel:{fontSize:9,color:colors.danger,fontWeight:"900",marginTop:4},
  addAttachment:{color:colors.orangeDark,fontWeight:"900",textAlign:"right",writingDirection:"rtl"},
  error:{color:colors.danger,textAlign:"right",writingDirection:"rtl"},
  closed:{backgroundColor:colors.greenSoft,borderRadius:radius.md,padding:14,marginTop:12},
  closedTitle:{fontWeight:"900",color:colors.greenDark,textAlign:"right",writingDirection:"rtl"},
  closedText:{fontSize:12,color:colors.muted,textAlign:"right",writingDirection:"rtl",marginTop:5},
});
