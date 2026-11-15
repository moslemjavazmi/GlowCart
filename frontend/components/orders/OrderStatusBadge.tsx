
import type { OrderStatus } from "@/lib/redux/features/orders/orderTypes";

const STATUS_CONFIG: Record<
  OrderStatus,
  {
    label: string;
    className: string;
  }
> = {
  pending: {
    label: "در انتظار پرداخت",
    className: "bg-amber-50 text-amber-700",
  },

  awaiting_payment: {
    label: "در انتظار پرداخت",
    className: "bg-amber-50 text-amber-700",
  },

  paid: {
    label: "پرداخت شده",
    className: "bg-green-50 text-green-700",
  },

  processing: {
    label: "در حال پردازش",
    className: "bg-blue-50 text-blue-700",
  },

  shipped: {
    label: "ارسال شده",
    className: "bg-indigo-50 text-indigo-700",
  },

  delivered: {
    label: "تحویل داده شده",
    className: "bg-emerald-50 text-emerald-700",
  },

  cancelled: {
    label: "لغو شده",
    className: "bg-red-50 text-red-700",
  },

  refunded: {
    label: "مبلغ بازپرداخت شده",
    className: "bg-purple-50 text-purple-700",
  },

  expired: {
    label: "منقضی شده",
    className: "bg-gray-100 text-gray-600",
  },
};

interface OrderStatusBadgeProps {
  status: OrderStatus;
}

export default function OrderStatusBadge({
  status,
}: OrderStatusBadgeProps) {
  const config = STATUS_CONFIG[status];

  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1.5 text-xs font-semibold ${config.className}`}
    >
      {config.label}
    </span>
  );
}
