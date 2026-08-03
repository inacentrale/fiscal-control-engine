import React from "react";

type ColumnConfig = {
  label: string;
  width?: string;
};

type TableProps<T> = {
  data: T[] | any[];
  columns: (string | ColumnConfig)[];
  RowComponent: React.ComponentType<{ item: T }>;
};

const Table = <T,>({ data, columns, RowComponent }: TableProps<T>) => {
  return (
    <div className="overflow-x-auto scrollbar-thin w-full mt-8 mb-5">
      <table className="w-[600px] min-w-full table-fixed text-[14px] sm:text-[15px] border-collapse whitespace-nowrap">
        <thead className="bg-black/5 text-left text-black">
          <tr className="*:py-2 *:font-medium sm:*:py-3">
            {columns.map((column, index) => {
              const isString = typeof column === "string";
              const label = isString ? column : column.label;
              const width = isString ? undefined : column.width;

              return (
                <th
                  key={index}
                  className={`pl-3 ${
                    index === 0
                      ? "rounded-s-lg"
                      : index === columns.length - 1
                        ? "rounded-e-lg text-center"
                        : ""
                  }`}
                  style={width ? { width } : undefined}
                >
                  {label}
                </th>
              );
            })}
          </tr>
        </thead>

        <tbody className="text-black/85">
          {data.map((item, index) => (
            <RowComponent key={index} item={item} />
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Table;
