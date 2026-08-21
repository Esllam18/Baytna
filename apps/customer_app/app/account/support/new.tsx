import React, { useState } from "react";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import * as ImagePicker from "expo-image-picker";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Screen } from "../../../src/ui/Screen";
import { FormField } from "../../../src/ui/FormField";
import { PrimaryButton } from "../../../src/ui/PrimaryButton";
import { customerApi } from "../../../src/api";
import { SupportTicketCreate } from "../../../src/api/types";
import { queryKeys } from "../../../src/query/keys";
import { uploadSupportAttachment, LocalAttachment } from "../../../src/media/uploadSupportAttachment";
import { colors, radius, spacing } from "../../../src/theme/tokens";

const CATEGORIES: { value: SupportTicketCreate["category"]; label: string }[] = [
  { value: "food_quality", label: "جودة الأكل" },
  { value: "missing_item", label: "عنصر ناقص" },
  { value: "wrong_item", label: "طلب خاطئ" },
  { value: "late_delivery", label: "تأخير" },
  { value: "delivery_issue", label: "توصيل" },
  { value: "refund", label: "استرداد" },
  { value: "payment", label: "دفع" },
  { value: "app_issue", label: "التطبيق" },
  { value: "other", label: "أخرى" },
];

export default function NewSupportTicketScreen() {
  const { orderId } = useLocalSearchParams<{ orderId?: string }>();
  const linkedOrderId = String(orderId ?? "").trim() || null;
  const [category, setCategory] = useState<SupportTicketCreate["category"]>("other");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<SupportTicketCreate["priority"]>("normal");
  const [attachments, setAttachments] = useState<LocalAttachment[]>([]);
  const [attachmentError, setAttachmentError] = useState("");
  const qc = useQueryClient();

  const chooseImage = async () => {
    setAttachmentError("");
    if (attachments.length >= 5) {
      setAttachmentError("الحد الأقصى 5 صور.");
      return;
    }
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setAttachmentError("اسمح بالوصول للصور علشان تضيف مرفق.");
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
      setAttachmentError("الصيغة غير مدعومة. استخدم JPG أو PNG أو WebP.");
      return;
    }
    setAttachments((current) => [
      ...current,
      {
        uri: asset.uri,
        fileName: asset.fileName ?? "support-image.jpg",
        mimeType,
        fileSize: asset.fileSize,
      },
    ]);
  };

  const create = useMutation({
    mutationFn: async () => {
      const uploadedIds: string[] = [];
      for (const attachment of attachments) {
        const asset = await uploadSupportAttachment(attachment);
        uploadedIds.push(asset.id);
      }
      return customerApi.createSupportTicket({
        order_id: linkedOrderId,
        category,
        subject: subject.trim(),
        description: description.trim(),
        priority,
        attachment_ids: uploadedIds,
      });
    },
    onSuccess: async (ticket) => {
      await qc.invalidateQueries({ queryKey: queryKeys.supportTickets });
      router.replace(`/account/support/${ticket.id}`);
    },
  });

  return (
    <Screen>
      <View style={s.header}>
        <Text onPress={() => router.back()} style={s.back}>→</Text>
        <Text style={s.title}>طلب دعم جديد</Text>
      </View>

      {linkedOrderId ? (
        <View style={s.linkedOrder}>
          <Text style={s.linkedOrderText}>
            طلب مرتبط #{linkedOrderId.slice(0, 8).toUpperCase()}
          </Text>
        </View>
      ) : null}

      <Text style={s.label}>نوع المشكلة</Text>
      <View style={s.chips}>
        {CATEGORIES.map((item) => (
          <Pressable
            key={item.value}
            onPress={() => setCategory(item.value)}
            style={[s.chip, category === item.value && s.chipActive]}
          >
            <Text style={[s.chipText, category === item.value && s.chipTextActive]}>
              {item.label}
            </Text>
          </Pressable>
        ))}
      </View>

      <View style={s.form}>
        <FormField
          label="عنوان المشكلة"
          value={subject}
          onChangeText={setSubject}
          placeholder="مثال: عنصر ناقص من الطلب"
        />
        <FormField
          label="اشرح لنا اللي حصل"
          value={description}
          onChangeText={setDescription}
          placeholder="اكتب التفاصيل..."
          multiline
        />

        <Text style={s.label}>صور توضيحية — اختياري</Text>
        <View style={s.attachmentRow}>
          {attachments.map((item, index) => (
            <Pressable
              key={`${item.uri}-${index}`}
              onPress={() => setAttachments((cur) => cur.filter((_, i) => i !== index))}
              style={s.previewWrap}
            >
              <Image source={{ uri: item.uri }} style={s.preview} />
              <Text style={s.remove}>×</Text>
            </Pressable>
          ))}
          {attachments.length < 5 ? (
            <Pressable onPress={() => void chooseImage()} style={s.addPhoto}>
              <Text style={s.addPhotoIcon}>＋</Text>
              <Text style={s.addPhotoText}>صورة</Text>
            </Pressable>
          ) : null}
        </View>
        {attachmentError ? <Text style={s.error}>{attachmentError}</Text> : null}

        <Text style={s.label}>الأولوية</Text>
        <View style={s.priority}>
          <Priority label="عادي" active={priority === "normal"} onPress={() => setPriority("normal")} />
          <Priority label="مهم" active={priority === "high"} onPress={() => setPriority("high")} />
          <Priority label="عاجل" active={priority === "urgent"} onPress={() => setPriority("urgent")} />
        </View>

        {create.isError ? (
          <Text style={s.error}>تعذر رفع المرفقات أو إرسال طلب الدعم.</Text>
        ) : null}

        <PrimaryButton
          label={attachments.length ? `رفع ${attachments.length} صورة وإرسال` : "إرسال للدعم"}
          onPress={() => create.mutate()}
          loading={create.isPending}
          disabled={subject.trim().length < 3 || description.trim().length < 3}
        />
      </View>
    </Screen>
  );
}

function Priority({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress(): void;
}) {
  return (
    <Pressable onPress={onPress} style={[s.priorityChip, active && s.priorityActive]}>
      <Text style={[s.priorityText, active && s.priorityTextActive]}>{label}</Text>
    </Pressable>
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
  header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:14,paddingBottom:18},
  back:{fontSize:26},
  title:{flex:1,fontSize:22,fontWeight:"900",color:colors.ink,textAlign:"right"},
  label:{fontSize:12,fontWeight:"800",color:colors.ink,textAlign:"right",writingDirection:"rtl",marginBottom:7},
  chips:{flexDirection:"row-reverse",flexWrap:"wrap",gap:7},
  chip:{borderRadius:radius.pill,backgroundColor:colors.soft,paddingHorizontal:11,paddingVertical:8},
  chipActive:{backgroundColor:colors.orangeSoft},
  chipText:{fontSize:10,color:colors.muted},
  chipTextActive:{color:colors.orangeDark,fontWeight:"900"},
  form:{gap:spacing.md,marginTop:18},
  priority:{flexDirection:"row-reverse",gap:8},
  priorityChip:{flex:1,alignItems:"center",borderRadius:radius.md,borderWidth:1,borderColor:colors.border,paddingVertical:10},
  priorityActive:{borderColor:colors.orange,backgroundColor:colors.orangeSoft},
  priorityText:{fontSize:11,color:colors.muted},
  priorityTextActive:{color:colors.orangeDark,fontWeight:"900"},
  attachmentRow:{flexDirection:"row-reverse",flexWrap:"wrap",gap:8},
  previewWrap:{position:"relative"},
  preview:{width:66,height:66,borderRadius:14,backgroundColor:colors.soft},
  remove:{position:"absolute",top:-6,right:-6,width:21,height:21,borderRadius:11,backgroundColor:colors.danger,color:"#fff",fontWeight:"900",textAlign:"center",lineHeight:20},
  addPhoto:{width:66,height:66,borderRadius:14,borderWidth:1,borderStyle:"dashed",borderColor:colors.orange,alignItems:"center",justifyContent:"center",backgroundColor:colors.orangeSoft},
  addPhotoIcon:{fontSize:21,color:colors.orangeDark},
  addPhotoText:{fontSize:9,color:colors.orangeDark,fontWeight:"900"},
  error:{color:colors.danger,textAlign:"right",writingDirection:"rtl"},
  linkedOrder:{backgroundColor:colors.greenSoft,borderRadius:radius.md,padding:10,marginBottom:12},
  linkedOrderText:{color:colors.greenDark,fontWeight:"900",textAlign:"right",writingDirection:"rtl"},
});
