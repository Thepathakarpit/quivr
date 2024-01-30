import { AiOutlineLoading3Quarters } from "react-icons/ai";
import { FaCheckCircle, FaHome, FaRegUserCircle } from "react-icons/fa";
import { FaArrowUpFromBracket } from "react-icons/fa6";
import { IconType } from "react-icons/lib";
import {
  LuBrain,
  LuChevronDown,
  LuChevronRight,
  LuCopy,
  LuFile,
  LuPlusCircle,
  LuSearch,
} from "react-icons/lu";
import { MdDelete, MdEdit, MdHistory } from "react-icons/md";
import { RiHashtag } from "react-icons/ri";

export const iconList: { [name: string]: IconType } = {
  add: LuPlusCircle,
  brain: LuBrain,
  checkCircle: FaCheckCircle,
  chevronDown: LuChevronDown,
  chevronRight: LuChevronRight,
  copy: LuCopy,
  delete: MdDelete,
  edit: MdEdit,
  file: LuFile,
  followUp: FaArrowUpFromBracket,
  hastag: RiHashtag,
  history: MdHistory,
  home: FaHome,
  loader: AiOutlineLoading3Quarters,
  search: LuSearch,
  user: FaRegUserCircle,
};
