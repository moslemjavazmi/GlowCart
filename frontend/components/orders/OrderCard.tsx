
import Link from "next/link";

import type { Order } from "@/lib/redux/features/orders/orderTypes";

import OrderStatusBadge from "./OrderStatusBadge";

interface OrderCardProps {
  order: Order;
}

export default function OrderCard({
  order,
}: OrderCardProps) {
  const formattedDate = new Date(
    order.created_at
  ).toLocaleDateString("fa-IR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <article className="rounded-2xl border border-gray-100 bg-white p-5 transition hover:border-pink-100 hover:shadow-sm sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs text-gray-400">
            شماره سفارش
          </p>

          <h2 className="mt-1 font-bold text-gray-900">
            {order.order_number}
          </h2>
        </div>

        <OrderStatusBadge status={order.status} />
      </div>

      <div className="mt-5 grid gap-4 border-y border-gray-100 py-4 sm:grid-cols-2">
        <div>
          <p className="text-xs text-gray-400">
            تاریخ ثبت سفارش
          </p>

          <p className="mt-1 text-sm font-medium text-gray-700">
            {formattedDate}
          </p>
        </div>

        <div>
          <p className="text-xs text-gray-400">
            تعداد محصولات
          </p>

          <p className="mt-1 text-sm font-medium text-gray-700">
            {order.items.reduce(
              (total, item) => total + item.quantity,
              0
            ).toLocaleString("fa-IR")}
            {" عدد"}
          </p>
        </div>

        <div>
          <p className="text-xs text-gray-400">
            مبلغ سفارش
          </p>

          <p className="mt-1 text-sm font-bold text-gray-900">
            {Number(
              order.total_amount
            ).toLocaleString("fa-IR")}
            {" تومان"}
          </p>
        </div>

        <div>
          <p className="text-xs text-gray-400">
            گیرنده
          </p>

          <p className="mt-1 text-sm font-medium text-gray-700">
            {order.recipient_name || "—"}
          </p>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-gray-400">
          {order.items.length.toLocaleString("fa-IR")}
          {" نوع محصول"}
        </p>

        <Link
          href={`/orders/${order.id}`}
          className="rounded-xl bg-pink-600 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-pink-700"
        >
          مشاهده جزئیات
        </Link>
      </div>
    </article>
  );
}
